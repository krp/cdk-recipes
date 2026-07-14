---
tags: compute, lambda, storage
---

# S3-Triggered Lambda with Cross-Bucket Processing

A Lambda function triggered by S3 object creation events that reads the object from an input bucket, processes it, and writes results to an output bucket.

## Code

```python
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
)
from constructs import Construct


class S3ProcessorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        input_bucket = s3.Bucket(self, "InputBucket")
        output_bucket = s3.Bucket(self, "OutputBucket")

        processor = lambda_.Function(
            self,
            "Processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/processor"),
        )

        input_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor),
        )

        input_bucket.grant_read(processor)
        output_bucket.grant_write(processor)
```

The handler code at `lambda/processor/index.py`:

```python
import boto3
import json

s3 = boto3.client("s3")


def handler(event, context):
    for record in event["Records"]:
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = record["s3"]["object"]["key"]

        # Read the object from the input bucket
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        content = response["Body"].read().decode("utf-8")

        # Process (example: reverse the content)
        processed = content[::-1]

        # Write to the output bucket
        output_key = f"processed/{object_key}"
        s3.put_object(
            Bucket=output_bucket_name,  # injected via env var or context
            Key=output_key,
            Body=processed.encode("utf-8"),
        )

    return {"statusCode": 200, "processed": len(event["Records"])}
```

Pass the output bucket name to the function via environment variables:

```python
processor.add_environment("OUTPUT_BUCKET", output_bucket.bucket_name)
```

## What's Happening

- **`add_event_notification()`** with `s3n.LambdaDestination(processor)` does two things: (1) adds a `AWS::S3::Bucket.NotificationConfiguration` entry that tells S3 to publish `OBJECT_CREATED` events to the Lambda function, and (2) grants the S3 service principal `lambda:InvokeFunction` permission via a `AWS::Lambda::Permission` resource on the function.

- **The event payload** contains `event["Records"]`, each with `s3.bucket.name` and `s3.object.key` — the bucket name and object key that S3 includes in the notification. Use these fields rather than raw event body parsing, as S3 may encode special characters in the key (e.g., spaces as `+`). Retrieve the object using these values with `boto3.client("s3").get_object()`.

- **`grant_read()`** adds an IAM policy statement to the Lambda execution role allowing `s3:GetObject` (and `s3:GetObjectVersion`) on the input bucket's objects. **`grant_write()`** adds `s3:PutObject` on the output bucket. These are CDK L2 grant methods that generate minimally scoped IAM policy statements — `grant_read` scopes to `arn:aws:s3:::<bucket>/*` and `grant_write` scopes similarly.

- **Error handling**: When the Lambda invocation fails or times out, S3 retries the event notification based on the Lambda function's `retry_attempts` (defaults to 2, configurable via `event_retry_attempts` property on `LambdaDestination`). After exhausting retries, S3 can send the failed event to a dead-letter queue if one is configured on the notification.

- **Async processing**: For workloads where sustained failures could lose data, route the S3 events through SQS instead: S3 → SQS → Lambda. SQS provides a persistent queue with configurable retention (up to 14 days), DLQ support, and batch processing. Use `s3n.SqsDestination()` and subscribe the Lambda to the SQS queue.

### Key CDK Concepts

- `LambdaDestination` is a notification destination — it does not create the Lambda function. The function must exist before or at the same time as the notification.
- `grant_read()` and `grant_write()` use the `add_to_principal_policy()` pattern under the hood, appending to the function role's policy document.
- S3 event notifications are eventually consistent — there is no guarantee a notification fires for every object write, though in practice delays are sub-second.

## Cross-Refs

See [[lambda-hello-python]] for Lambda function basics.
See [[s3-event-notifications]] for the full range of S3 event types and filtering (prefix, suffix).
See [[async-pipeline-s3-sqs-lambda-ddb]] for the async S3 → SQS → Lambda pattern with DynamoDB persistence.
