import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack


def create_test_stack() -> CdkMailToSlackStack:
    app = cdk.App()
    return CdkMailToSlackStack(
        app,
        "TestStack",
        domain_name="test.example.com",
        hosted_zone_name="example.com",
        slack_error_channel="errors",
        create_mx_record=False,
        use_existing_rule_set=False,
        existing_rule_set_name="",
        sentry_dsn="",
    )


def test_s3_bucket_created() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    # Should have 2 buckets: email bucket and access log bucket
    template.resource_count_is("AWS::S3::Bucket", 2)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": Match.any_value()
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "ExpirationInDays": 30,
                        "Id": "DeleteAfter30Days",
                        "Status": "Enabled",
                    }
                ]
            },
        },
    )


def test_lambda_function_created() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    # Note: CDK creates additional Lambda functions for custom resources
    # (S3 notifications). We verify our main Lambda function exists with
    # the correct properties
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.14",
            "Handler": "main.handler",
            "Timeout": 30,
            "MemorySize": 128,
            "ReservedConcurrentExecutions": 10,
            "Environment": {
                "Variables": {
                    "DOMAIN_NAME": "test.example.com",
                    "SLACK_BOT_TOKEN_SECRET_NAME": "MailSlack/SlackBotToken",
                    "SLACK_ERROR_CHANNEL": "errors",
                    "LOG_LEVEL": "INFO",
                    "POWERTOOLS_SERVICE_NAME": "email-to-slack",
                }
            },
        },
    )


def test_ses_receipt_rule_set_created() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::SES::ReceiptRuleSet", 1)
    template.has_resource_properties(
        "AWS::SES::ReceiptRuleSet",
        {"RuleSetName": "MailSlackRuleSet"},
    )


def test_ses_receipt_rule_created() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::SES::ReceiptRule", 1)
    template.has_resource_properties(
        "AWS::SES::ReceiptRule",
        {
            "Rule": {
                "Actions": [
                    {
                        "S3Action": {
                            "BucketName": Match.any_value(),
                            "ObjectKeyPrefix": "ses-emails/",
                        }
                    }
                ],
                "Recipients": ["test.example.com"],
            }
        },
    )


def test_lambda_has_s3_read_permission() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    # Verify Lambda has S3 read permissions (grant_read adds GetObject*)
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        {
                            "Action": ["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                            "Effect": "Allow",
                            "Resource": Match.any_value(),
                        }
                    ]
                )
            }
        },
    )


def test_lambda_has_secrets_manager_permission() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": Match.array_with(
                                    ["secretsmanager:GetSecretValue"]
                                ),
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_s3_bucket_has_ssl_enforcement() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    # Check that bucket policy enforces SSL
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "s3:*",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                                "Effect": "Deny",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_lambda_has_sentry_dsn_when_provided() -> None:
    app = cdk.App()
    stack = CdkMailToSlackStack(
        app,
        "TestStack",
        domain_name="test.example.com",
        hosted_zone_name="example.com",
        slack_error_channel="errors",
        create_mx_record=False,
        use_existing_rule_set=False,
        existing_rule_set_name="",
        sentry_dsn="https://test@sentry.io/123",
    )
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": Match.object_like(
                    {"SENTRY_DSN": "https://test@sentry.io/123"}
                )
            }
        },
    )


def test_lambda_has_no_sentry_dsn_when_not_provided() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    # Get all Lambda functions
    functions = template.find_resources("AWS::Lambda::Function")
    for logical_id, resource in functions.items():
        env_vars = (
            resource.get("Properties", {}).get("Environment", {}).get("Variables", {})
        )
        # SENTRY_DSN should not be present
        assert "SENTRY_DSN" not in env_vars


def test_ses_receipt_rule_has_tls_and_scan_enabled() -> None:
    stack = create_test_stack()
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::SES::ReceiptRule",
        {
            "Rule": Match.object_like(
                {
                    "TlsPolicy": "Require",
                    "ScanEnabled": True,
                }
            )
        },
    )
