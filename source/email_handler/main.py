import json
import os
import re
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = Logger()
tracer = Tracer()

s3_client = boto3.client("s3")
secrets_client = boto3.client("secretsmanager")

# Initialize Sentry if DSN is provided
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[AwsLambdaIntegration()],
        traces_sample_rate=1.0,
    )


def get_slack_token() -> str:
    """Get Slack bot token from Secrets Manager.

    Note: Not traced with @tracer.capture_method to avoid exposing
    the token in X-Ray traces. Secrets Manager API calls are still
    automatically traced by X-Ray.
    """
    secret_name = os.environ["SLACK_BOT_TOKEN_SECRET_NAME"]
    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return str(secret["SLACK_BOT_TOKEN"])


@tracer.capture_method
def decode_mime_header(header: str) -> str:
    """Decode MIME encoded header (RFC 2047)."""
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)


@tracer.capture_method
def extract_channel_from_email(to_address: str, domain: str) -> str:
    match = re.match(rf"(.+)@{re.escape(domain)}", to_address)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid email format: {to_address}")


@tracer.capture_method
def parse_email_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
    return ""


@tracer.capture_method
def post_to_slack(
    client: WebClient, channel: str, from_addr: str, subject: str, body: str
) -> None:
    text = f"*From:* {from_addr}\n*Subject:* {subject}\n\n{body}"
    client.chat_postMessage(channel=channel, text=text)


@tracer.capture_method
def post_error_to_slack(
    client: WebClient, error_channel: str, original_channel: str, error_msg: str
) -> None:
    text = f"*Error posting to channel:* #{original_channel}\n*Error:* {error_msg}"
    client.chat_postMessage(channel=error_channel, text=text)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    try:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        logger.info(f"Processing email from s3://{bucket}/{key}")

        response = s3_client.get_object(Bucket=bucket, Key=key)
        email_content = response["Body"].read()
        msg = message_from_bytes(email_content)

        to_address = msg.get("To", "")
        from_address = msg.get("From", "")
        subject = decode_mime_header(msg.get("Subject", ""))

        # Skip AWS SES setup notification emails
        if (
            from_address == "Amazon Web Services <no-reply-aws@amazon.com>"
            and subject == "Amazon SES Setup Notification"
        ):
            logger.info("Skipping AWS SES setup notification email")
            return {"statusCode": 200, "body": "Skipped setup notification"}

        body = parse_email_body(msg)

        domain = os.environ["DOMAIN_NAME"]
        error_channel = os.environ["SLACK_ERROR_CHANNEL"]

        channel = extract_channel_from_email(to_address, domain)
        logger.info(f"Target channel: {channel}")

        slack_token = get_slack_token()
        slack_client = WebClient(token=slack_token)

        try:
            post_to_slack(slack_client, channel, from_address, subject, body)
            logger.info(f"Successfully posted to #{channel}")
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            post_error_to_slack(
                slack_client, error_channel, channel, e.response["error"]
            )

        return {"statusCode": 200, "body": "Success"}

    except Exception:
        logger.exception("Unexpected error")
        raise
