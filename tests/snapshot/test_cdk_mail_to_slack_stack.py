import aws_cdk as cdk
from aws_cdk.assertions import Template

from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack

# CI configuration - does not depend on local config.py
CI_CONFIG = {
    "domain_name": "test.example.com",
    "hosted_zone_name": "example.com",
    "slack_error_channel": "errors",
    "create_mx_record": True,
    "use_existing_rule_set": False,
    "existing_rule_set_name": "",
    "sentry_dsn": "",
}


def test_snapshot(snapshot) -> None:
    """Test CloudFormation template snapshot.

    This test captures the entire CloudFormation template as a snapshot.
    If the template changes, the test will fail and show the diff.
    Run `pytest --snapshot-update` to update the snapshot after reviewing changes.

    Note: Uses CI_CONFIG to avoid dependency on local config.py
    """
    app = cdk.App()
    stack = CdkMailToSlackStack(
        app,
        "TestStack",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
        **CI_CONFIG
    )
    template = Template.from_stack(stack)
    assert template.to_json() == snapshot
