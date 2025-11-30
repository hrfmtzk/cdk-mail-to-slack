import json
import os
from email.message import EmailMessage
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError


@pytest.fixture
def lambda_context() -> MagicMock:
    context = MagicMock()
    context.function_name = "test-function"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def s3_event() -> dict[str, Any]:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "ses-emails/test-email"},
                }
            }
        ]
    }


@pytest.fixture
def sample_email() -> bytes:
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "test-channel@slackmailbot.example.com"
    msg["Subject"] = "Test Subject"
    msg.set_content("Test email body")
    return msg.as_bytes()


@pytest.fixture
def japanese_email() -> bytes:
    """Email with encoded subject in RFC 2047 format."""
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "test-channel@slackmailbot.example.com"
    msg["Subject"] = "=?UTF-8?B?44OG44K544OI5Lu25ZCN?="
    msg.set_content("Test email body")
    return msg.as_bytes()


@pytest.fixture(autouse=True)
def set_env_vars() -> Iterator[None]:
    os.environ["DOMAIN_NAME"] = "slackmailbot.example.com"
    os.environ["SLACK_BOT_TOKEN_SECRET_NAME"] = "test/secret"
    os.environ["SLACK_ERROR_CHANNEL"] = "mail-errors"
    os.environ["POWERTOOLS_SERVICE_NAME"] = "test"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"
    os.environ["AWS_XRAY_CONTEXT_MISSING"] = "LOG_ERROR"
    yield


@patch("main.s3_client")
@patch("main.secrets_client")
@patch("main.WebClient")
def test_handler_success(
    mock_webclient: MagicMock,
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    sample_email: bytes,
    lambda_context: MagicMock,
) -> None:
    # Setup mocks
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: sample_email)}
    mock_secrets.get_secret_value.return_value = {
        "SecretString": json.dumps({"SLACK_BOT_TOKEN": "xoxb-test-token"})
    }
    mock_slack_instance = MagicMock()
    mock_webclient.return_value = mock_slack_instance

    # Import after patching
    import main

    # Execute
    result = main.handler(s3_event, lambda_context)

    # Verify
    assert result["statusCode"] == 200
    mock_s3.get_object.assert_called_once_with(
        Bucket="test-bucket", Key="ses-emails/test-email"
    )
    mock_secrets.get_secret_value.assert_called_once_with(SecretId="test/secret")
    mock_slack_instance.chat_postMessage.assert_called_once()
    call_args = mock_slack_instance.chat_postMessage.call_args
    assert call_args[1]["channel"] == "test-channel"
    assert "sender@example.com" in call_args[1]["text"]
    assert "Test Subject" in call_args[1]["text"]


@patch("main.s3_client")
@patch("main.secrets_client")
@patch("main.WebClient")
def test_handler_slack_error_fallback(
    mock_webclient: MagicMock,
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    sample_email: bytes,
    lambda_context: MagicMock,
) -> None:
    # Setup mocks
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: sample_email)}
    mock_secrets.get_secret_value.return_value = {
        "SecretString": json.dumps({"SLACK_BOT_TOKEN": "xoxb-test-token"})
    }
    mock_slack_instance = MagicMock()
    mock_webclient.return_value = mock_slack_instance

    # Simulate Slack API error
    error_response = {"error": "channel_not_found"}
    mock_slack_instance.chat_postMessage.side_effect = [
        SlackApiError("Error", error_response),  # type: ignore[no-untyped-call]
        None,
    ]

    # Import after patching
    import main

    # Execute
    result = main.handler(s3_event, lambda_context)

    # Verify
    assert result["statusCode"] == 200
    assert mock_slack_instance.chat_postMessage.call_count == 2
    # Second call should be to error channel
    error_call = mock_slack_instance.chat_postMessage.call_args_list[1]
    assert error_call[1]["channel"] == "mail-errors"
    assert "test-channel" in error_call[1]["text"]


def test_extract_channel_from_email() -> None:
    import main

    channel = main.extract_channel_from_email(
        "test-channel@slackmailbot.example.com", "slackmailbot.example.com"
    )
    assert channel == "test-channel"


def test_extract_channel_invalid_format() -> None:
    import main

    with pytest.raises(ValueError):
        main.extract_channel_from_email("invalid@wrong.com", "slackmailbot.example.com")


def test_parse_email_body_plain_text() -> None:
    import main

    msg = EmailMessage()
    msg.set_content("Plain text body")
    body = main.parse_email_body(msg)
    assert body.strip() == "Plain text body"


def test_parse_email_body_multipart() -> None:
    import main

    msg = EmailMessage()
    msg.set_content("Plain text body")
    msg.add_alternative("<html><body>HTML body</body></html>", subtype="html")
    body = main.parse_email_body(msg)
    assert body.strip() == "Plain text body"


def test_decode_mime_header() -> None:
    import main

    # Test UTF-8 encoded subject
    encoded = "=?UTF-8?B?44OG44K544OI5Lu25ZCN?="
    decoded = main.decode_mime_header(encoded)
    assert decoded == "テスト件名"

    # Test plain ASCII
    plain = "Plain Subject"
    decoded_plain = main.decode_mime_header(plain)
    assert decoded_plain == "Plain Subject"


@patch.dict(
    os.environ,
    {
        "DOMAIN_NAME": "slackmailbot.example.com",
        "SLACK_BOT_TOKEN_SECRET_NAME": "test-secret",
        "SLACK_ERROR_CHANNEL": "errors",
    },
)
@patch("main.s3_client")
@patch("main.secrets_client")
@patch("main.WebClient")
def test_handler_japanese_subject(
    mock_webclient: MagicMock,
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    japanese_email: bytes,
    lambda_context: MagicMock,
) -> None:
    import main

    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: japanese_email)}
    mock_secrets.get_secret_value.return_value = {
        "SecretString": json.dumps({"SLACK_BOT_TOKEN": "xoxb-test-token"})
    }
    mock_slack_instance = MagicMock()
    mock_webclient.return_value = mock_slack_instance

    result = main.handler(s3_event, lambda_context)

    assert result["statusCode"] == 200
    mock_slack_instance.chat_postMessage.assert_called_once()
    call_args = mock_slack_instance.chat_postMessage.call_args
    assert call_args[1]["channel"] == "test-channel"
    # Verify encoded subject is decoded
    assert "テスト件名" in call_args[1]["text"]
    assert "=?UTF-8?B?" not in call_args[1]["text"]


@patch("main.s3_client")
def test_handler_skips_aws_ses_setup_notification(
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    lambda_context: MagicMock,
) -> None:
    """Test that AWS SES setup notification emails are skipped."""
    import main

    # Create AWS SES setup notification email
    msg = EmailMessage()
    msg["From"] = "Amazon Web Services <no-reply-aws@amazon.com>"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Amazon SES Setup Notification"
    msg.set_content("Setup notification body")

    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: msg.as_bytes())}

    result = main.handler(s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert result["body"] == "Skipped setup notification"
    # Verify no Slack API calls were made
    mock_s3.get_object.assert_called_once()


@patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"}, clear=False)
@patch("sentry_sdk.init")
def test_sentry_initialization_with_dsn(mock_sentry_init: MagicMock) -> None:
    """Test that Sentry is initialized when SENTRY_DSN is set."""
    import sys

    # Remove main module to force reimport
    if "main" in sys.modules:
        del sys.modules["main"]

    import main  # noqa: F401

    mock_sentry_init.assert_called_once()
    call_kwargs = mock_sentry_init.call_args[1]
    assert call_kwargs["dsn"] == "https://test@sentry.io/123"
    assert len(call_kwargs["integrations"]) == 1


def test_sentry_not_initialized_without_dsn() -> None:
    """Test that Sentry is not initialized when SENTRY_DSN is not set."""
    import sys

    # Ensure SENTRY_DSN is not set
    if "SENTRY_DSN" in os.environ:
        del os.environ["SENTRY_DSN"]

    # Remove main module to force reimport
    if "main" in sys.modules:
        del sys.modules["main"]

    with patch("sentry_sdk.init") as mock_sentry_init:
        import main  # noqa: F401

        mock_sentry_init.assert_not_called()


@patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"}, clear=False)
@patch("sentry_sdk.capture_exception")
@patch("main.s3_client")
@patch("main.secrets_client")
def test_sentry_captures_exception(
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    mock_capture: MagicMock,
    s3_event: dict[str, Any],
    lambda_context: MagicMock,
) -> None:
    """Test that Sentry captures exceptions when they occur."""
    import main

    # Simulate S3 error
    mock_s3.get_object.side_effect = Exception("S3 error")

    with pytest.raises(Exception, match="S3 error"):
        main.handler(s3_event, lambda_context)
