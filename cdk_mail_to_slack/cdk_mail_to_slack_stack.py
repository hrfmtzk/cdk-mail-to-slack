from typing import Any

from aws_cdk import (
    Duration,
    RemovalPolicy,
    SecretValue,
    Stack,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_route53 as route53,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_secretsmanager as secretsmanager,
    aws_ses as ses,
    aws_ses_actions as ses_actions,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from cdk_nag import NagPackSuppression, NagSuppressions, RegexAppliesTo
from constructs import Construct


class CdkMailToSlackStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        domain_name: str,
        hosted_zone_name: str,
        slack_error_channel: str,
        create_mx_record: bool = True,
        use_existing_rule_set: bool = False,
        existing_rule_set_name: str = "",
        insert_after_rule: str = "",
        enable_xray_tracing: bool = True,
        sentry_dsn: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Slack Bot Token secret name (fixed)
        slack_bot_token_secret_name = "MailSlack/SlackBotToken"

        # S3 bucket for access logs
        access_log_bucket = s3.Bucket(
            self,
            "MailSlackAccessLogBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter90Days",
                    expiration=Duration.days(90),
                    enabled=True,
                )
            ],
        )

        # S3 bucket for storing emails
        email_bucket = s3.Bucket(
            self,
            "MailSlackS3Bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            server_access_logs_bucket=access_log_bucket,
            server_access_logs_prefix="email-bucket-logs/",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter30Days",
                    expiration=Duration.days(30),
                    enabled=True,
                )
            ],
        )

        # Create Slack Bot Token secret
        slack_secret = secretsmanager.Secret(
            self,
            "SlackBotToken",
            secret_name=slack_bot_token_secret_name,
            description="Slack Bot Token for email notifications",
            secret_object_value={
                "SLACK_BOT_TOKEN": SecretValue.unsafe_plain_text(
                    "PLACEHOLDER-REPLACE-WITH-ACTUAL-TOKEN"
                )
            },
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Suppress cdk-nag warning for Secret rotation
        NagSuppressions.add_resource_suppressions(
            slack_secret,
            [
                NagPackSuppression(
                    id="AwsSolutions-SMG4",
                    reason=(
                        "Slack Bot Token is manually managed and does not "
                        "require automatic rotation"
                    ),
                ),
            ],
        )

        # CloudWatch Logs group for Lambda
        log_group = logs.LogGroup(
            self,
            "MailSlackLambdaLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Lambda function
        lambda_env = {
            "DOMAIN_NAME": domain_name,
            "SLACK_BOT_TOKEN_SECRET_NAME": slack_bot_token_secret_name,
            "SLACK_ERROR_CHANNEL": slack_error_channel,
            "LOG_LEVEL": "INFO",
            "POWERTOOLS_SERVICE_NAME": "email-to-slack",
        }
        if sentry_dsn:
            lambda_env["SENTRY_DSN"] = sentry_dsn

        email_handler = PythonFunction(
            self,
            "MailSlackLambdaFunction",
            entry="source/email_handler",
            runtime=lambda_.Runtime.PYTHON_3_14,
            index="main.py",
            handler="handler",
            timeout=Duration.seconds(30),
            memory_size=128,
            reserved_concurrent_executions=10,
            log_group=log_group,
            tracing=(
                lambda_.Tracing.ACTIVE
                if enable_xray_tracing
                else lambda_.Tracing.DISABLED
            ),
            environment=lambda_env,
        )

        # Grant permissions using CDK grant methods
        email_bucket.grant_read(email_handler, "ses-emails/*")
        slack_secret.grant_read(email_handler)

        # Suppress cdk-nag warnings for Lambda IAM role
        NagSuppressions.add_resource_suppressions(
            email_handler.role,  # type: ignore[arg-type]
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason=(
                        "AWSLambdaBasicExecutionRole is required for "
                        "CloudWatch Logs access"
                    ),
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaBasicExecutionRole"
                    ],
                ),
            ],
        )

        # Suppress cdk-nag warnings for S3 wildcard permissions
        # Note: Cannot use email_bucket.arn_for_objects() because it returns
        # a token that cdk-nag cannot match. Must use regex pattern instead.
        s3_applies_to: list[Any] = [
            "Action::s3:GetBucket*",
            "Action::s3:GetObject*",
            "Action::s3:List*",
            RegexAppliesTo(
                regex=(
                    "/^Resource::<MailSlackS3Bucket[A-Z0-9]+\\."
                    "Arn>\\/ses-emails\\/\\*$/"
                )
            ),
        ]
        # Add X-Ray wildcard permission if tracing is enabled
        if enable_xray_tracing:
            s3_applies_to.append("Resource::*")

        NagSuppressions.add_resource_suppressions(
            email_handler.role.node.find_child(  # type: ignore[union-attr]
                "DefaultPolicy"
            ),
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=(
                        "Wildcard permissions are generated by CDK "
                        "grant_read() method for S3 operations"
                        + (" and X-Ray tracing" if enable_xray_tracing else "")
                    ),
                    applies_to=s3_applies_to,
                ),
            ],
        )

        # S3 event notification
        email_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(email_handler),
            s3.NotificationKeyFilter(prefix="ses-emails/"),
        )

        # Common receipt rule configuration
        rule_actions = [
            ses_actions.S3(
                bucket=email_bucket,
                object_key_prefix="ses-emails/",
            )
        ]
        rule_recipients = [domain_name]

        # Get or create SES receipt rule set
        if use_existing_rule_set:
            if not existing_rule_set_name:
                raise ValueError(
                    "existing_rule_set_name must be specified when "
                    "use_existing_rule_set=True"
                )
            rule_set = ses.ReceiptRuleSet.from_receipt_rule_set_name(
                self, "MailSlackRuleSet", existing_rule_set_name
            )
        else:
            rule_set = ses.ReceiptRuleSet(
                self,
                "MailSlackRuleSet",
                receipt_rule_set_name="MailSlackRuleSet",
            )

        # Prepare after parameter for rule position
        after_rule = None
        if insert_after_rule:
            after_rule = ses.ReceiptRule.from_receipt_rule_name(
                self, "AfterRule", insert_after_rule
            )

        # Add rule to rule set
        rule_set.add_rule(
            "MailSlackRule",
            recipients=rule_recipients,
            actions=rule_actions,
            after=after_rule,
            tls_policy=ses.TlsPolicy.REQUIRE,
            scan_enabled=True,
        )

        # Create MX record if enabled
        if create_mx_record:
            hosted_zone = route53.HostedZone.from_lookup(
                self, "HostedZone", domain_name=hosted_zone_name
            )
            route53.MxRecord(
                self,
                "MailSlackMxRecord",
                zone=hosted_zone,
                record_name=domain_name,
                values=[
                    route53.MxRecordValue(
                        host_name=f"inbound-smtp.{self.region}.amazonaws.com",
                        priority=10,
                    )
                ],
            )

        # Suppress cdk-nag warnings for CDK-generated custom resources
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason=(
                        "CDK-generated custom resources require "
                        "AWSLambdaBasicExecutionRole"
                    ),
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaBasicExecutionRole"
                    ],
                ),
            ],
            apply_to_nested_stacks=True,
        )
