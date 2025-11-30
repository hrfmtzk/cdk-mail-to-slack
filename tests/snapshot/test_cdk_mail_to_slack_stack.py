import json
from typing import Any

import aws_cdk as cdk
from aws_cdk.assertions import Template

from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack

# CI configuration - does not depend on local config.py
CI_CONFIG: dict[str, str | bool] = {
    "domain_name": "test.example.com",
    "hosted_zone_name": "example.com",
    "slack_error_channel": "errors",
    "create_mx_record": True,
    "use_existing_rule_set": False,
    "existing_rule_set_name": "",
    "sentry_dsn": "",
}


def normalize_template(template: dict[str, Any]) -> dict[str, Any]:
    """Normalize template by removing dynamic values.

    Removes values that change on every build but don't represent
    infrastructure changes:
    - Lambda S3 object keys (code hashes)
    - Asset hashes in parameters
    """
    normalized: dict[str, Any] = json.loads(json.dumps(template))

    # Remove Lambda S3 object keys
    if "Resources" in normalized:
        for resource in normalized["Resources"].values():
            if resource.get("Type") == "AWS::Lambda::Function":
                if "Properties" in resource and "Code" in resource["Properties"]:
                    code = resource["Properties"]["Code"]
                    if "S3Key" in code:
                        code["S3Key"] = "NORMALIZED"

    # Remove asset hash parameters
    if "Parameters" in normalized:
        for param_name, param_value in normalized["Parameters"].items():
            if "AssetParameters" in param_name and "S3VersionKey" in param_name:
                param_value["Default"] = "NORMALIZED"

    return normalized


def test_snapshot(snapshot: Any) -> None:
    """Test CloudFormation template snapshot.

    This test captures the CloudFormation template structure as a snapshot,
    excluding dynamic values like Lambda code hashes.
    If the infrastructure changes, the test will fail and show the diff.
    Run `pytest --snapshot-update` to update the snapshot after reviewing changes.

    Note: Uses CI_CONFIG to avoid dependency on local config.py
    """
    app = cdk.App()
    stack = CdkMailToSlackStack(
        app,
        "TestStack",
        domain_name=str(CI_CONFIG["domain_name"]),
        hosted_zone_name=str(CI_CONFIG["hosted_zone_name"]),
        slack_error_channel=str(CI_CONFIG["slack_error_channel"]),
        create_mx_record=bool(CI_CONFIG["create_mx_record"]),
        use_existing_rule_set=bool(CI_CONFIG["use_existing_rule_set"]),
        existing_rule_set_name=str(CI_CONFIG["existing_rule_set_name"]),
        sentry_dsn=str(CI_CONFIG["sentry_dsn"]),
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    template = Template.from_stack(stack)
    template_dict = dict(template.to_json())
    normalized = normalize_template(template_dict)
    assert normalized == snapshot
