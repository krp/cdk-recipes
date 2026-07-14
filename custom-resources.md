---
tags: advanced
---

# Custom Resources

CloudFormation Custom Resources — calling a Lambda function during stack create, update, and delete to provision resources that CDK does not model natively.

## Code

```python
from aws_cdk import custom_resources as cr
from aws_cdk import aws_lambda as lambda_, aws_logs as logs

on_event = lambda_.Function(self, "OnEventHandler",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="index.handler",
    code=lambda_.Code.from_asset("lambda/cr"),
)

provider = cr.Provider(self, "MyProvider",
    on_event_handler=on_event,
    log_retention=logs.RetentionDays.ONE_WEEK,
)

resource = cr.CustomResource(self, "MyCustomResource",
    provider=provider,
    properties={"Key": "Value"},
    resource_type="Custom::MyResource",
)
```

The Lambda handler receives CloudFormation lifecycle events:

```python
# lambda/cr/index.py
import json


def handler(event, context):
    request_type = event["RequestType"]  # Create | Update | Delete
    properties = event["ResourceProperties"]
    physical_id = event.get("PhysicalResourceId")

    if request_type == "Create":
        # Provision the resource, return a physical resource ID
        physical_id = "my-resource-id"

    return {
        "PhysicalResourceId": physical_id,
        "Data": {"Attribute1": "value1"},
    }
```

Using the custom resource output in the same stack:

```python
resource = cr.CustomResource(self, "MyResource", ...)

# Access response attributes
attr_value = resource.get_att_string("Attribute1")

# Pass to another resource
queue = sqs.Queue(self, "Queue",
    queue_name=attr_value,
)
```

## What's Happening

- **`cr.Provider`** is CDK's L2 for the custom resource provider pattern. It creates: a Lambda function (the `on_event_handler`), an SQS queue for asynchronous invocation, an SNS topic for success/failure signaling, and IAM roles for each — approximately 6 CloudFormation resources. This replaces the legacy pattern of writing a `CustomResourceProvider` singleton Lambda manually.
- **`on_event_handler`**: The Lambda that receives CloudFormation `RequestType` events (`Create`, `Update`, `Delete`). It must return a physical resource ID (a stable identifier CloudFormation uses to track the resource across updates). If the Lambda does not return a `PhysicalResourceId`, CloudFormation treats the request as failed.
- **`cr.CustomResource`** creates the `AWS::CloudFormation::CustomResource` that invokes the provider. Changes to `properties` between stack updates trigger a new `Update` event on the Lambda. When a property name changes (not just its value), CloudFormation calls `Delete` with the old properties then `Create` with the new ones.
- **Lambda event payload**: The handler receives `RequestType`, `ResourceProperties`, `OldResourceProperties` (on Update), `PhysicalResourceId` (on Update/Delete), `StackId`, `RequestId`, and `ResourceType`. The handler must respond synchronously — CloudFormation waits for the Lambda to return before continuing the stack operation. If the Lambda takes longer than 1 hour, the stack update times out.
- **Response format**: The Lambda returns a dict with `PhysicalResourceId` (required on success), `Data` (optional attributes accessible via `get_att_string`), and optionally `Reason` (a failure reason string). For failures, raise an exception or call `cloudformation.send()` with a failure status — CDK's Provider SQS/SNS path handles async delivery.
- **`log_retention`**: CDK attaches a log retention Lambda that sets CloudWatch Logs retention on the provider's log group. Without this, the Lambda logs persist indefinitely.

### Key CDK Concepts

- The custom resource pattern is an escape hatch for anything CDK does not support natively: provisioning SaaS resources, waiting on external services, running database migrations, registering DNS entries, or calling third-party APIs during deployment.
- `get_att_string("Attribute")` returns a CDK token — it resolves to `Fn::GetAtt` in the synthesized template. CloudFormation resolves it after the custom resource Lambda returns.
- `resource_type="Custom::MyResource"` sets the CloudFormation resource type. The string after `Custom::` is arbitrary but must be unique per resource type in the stack. The type appears in CloudFormation stack events and drift detection.
- **Synchronous vs asynchronous**: The default provider calls the Lambda synchronously (the Lambda response determines success/failure). The Provider also supports an SQS-based async path where the Lambda writes the response to an S3 signed URL — the Provider polls the SQS queue to pick up the result. This is useful when the Lambda work exceeds the 15-minute invocation limit, but adds complexity.

## Cross-Refs

See [[escape-hatches]] for direct CloudFormation property overrides on L2 resources.
See [[lambda-hello-python]] for creating the Lambda function passed to the provider.
See [[async-pipeline-s3-sqs-lambda-ddb]] for an asynchronous workflow that uses SQS directly instead of a custom resource.
