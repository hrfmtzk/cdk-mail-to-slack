import aws_cdk as cdk
from aws_cdk.assertions import Template

from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack


def test_snapshot() -> None:
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
        sentry_dsn="",
    )
    template = Template.from_stack(stack)
    # Verify template can be generated
    assert template.to_json()
    # Verify key resources exist (2 buckets: email + access log)
    template.resource_count_is("AWS::S3::Bucket", 2)
    # Note: CDK creates additional Lambda functions for custom resources
    template.resource_count_is("AWS::SES::ReceiptRuleSet", 1)
