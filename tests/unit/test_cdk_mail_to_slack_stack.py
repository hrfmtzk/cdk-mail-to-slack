import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_mail_to_slack.cdk_mail_to_slack_stack import CdkMailToSlackStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_mail_to_slack/cdk_mail_to_slack_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkMailToSlackStack(app, "cdk-mail-to-slack")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
