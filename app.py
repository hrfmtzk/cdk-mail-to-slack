#!/usr/bin/env python3
import os
import warnings

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

import config
from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack

# Suppress typeguard warnings for CDK protocols
warnings.filterwarnings(
    "ignore",
    message="Typeguard cannot check.*protocol",
    category=UserWarning,
)

app = cdk.App()

stack = CdkMailToSlackStack(
    app,
    "CdkMailToSlackStack",
    domain_name=config.DOMAIN_NAME,
    hosted_zone_name=config.HOSTED_ZONE_NAME,
    slack_error_channel=config.SLACK_ERROR_CHANNEL,
    create_mx_record=config.CREATE_MX_RECORD,
    use_existing_rule_set=config.USE_EXISTING_RULE_SET,
    existing_rule_set_name=getattr(config, "EXISTING_RULE_SET_NAME", ""),
    insert_after_rule=getattr(config, "INSERT_AFTER_RULE", ""),
    enable_xray_tracing=getattr(config, "ENABLE_XRAY_TRACING", True),
    sentry_dsn=getattr(config, "SENTRY_DSN", ""),
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
