import aws_cdk as core
import aws_cdk.assertions as assertions

from cdkbasics.cdkbasics_stack import CdkbasicsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdkbasics/cdkbasics_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkbasicsStack(app, "cdkbasics")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
