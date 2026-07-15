---
tags:
  - event-driven
  - storage
  - compute
---

# Async Pipeline: S3 to SQS to Lambda to DynamoDB

An end-to-end asynchronous processing pipeline: S3 object uploads publish events to SQS, a Lambda function consumes them from the queue, processes the data, and writes results to DynamoDB — fully decoupled with a dead-letter queue for failure isolation.

## Code

```python
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_source,
    aws_dynamodb as ddb,
)
from constructs import Construct


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # DLQ for failed SQS deliveries (Lambda processing failures)
        dlq = sqs.Queue(
            self,
            "DLQ",
            retention_period=Duration.days(14),
        )

        # Processing queue with redrive after 3 failed Lambda invocations
        queue = sqs.Queue(
            self,
            "ProcessingQueue",
            visibility_timeout=Duration.seconds(60),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq,
            ),
        )

        # Source bucket — triggers pipeline on object uploads
        input_bucket = s3.Bucket(
            self,
            "InputBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        input_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(queue),
        )

        # DynamoDB table for processed results
        table = ddb.Table(
            self,
            "Results",
            partition_key=ddb.Attribute(
                name="pk",
                type=ddb.AttributeType.STRING,
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Processor function — reads from SQS, writes to DynamoDB
        processor = lambda_.Function(
            self,
            "Processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "import json\n"
                "def handler(event, context):\n"
                '    for record in event["Records"]:\n'
                "        body = json.loads(record[\"body\"])\n"
                '        print("processing:", body)\n'
            ),
        )
        queue.grant_consume_messages(processor)
        input_bucket.grant_read(processor)
        table.grant_write(processor)

        # Wire SQS as the event source for the Lambda
        lambda_event_source.SqsEventSource(queue).bind(processor)
```

## What's Happening

- **S3 → SQS notification:** `input_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3n.SqsDestination(queue))` configures S3 to send object-created events directly to the SQS queue. This bypasses Lambda entirely for ingestion — S3 publishes to SQS, and Lambda polls the queue independently. Unlike S3 → Lambda notifications (which retry up to 3 times synchronously), S3 → SQS decouples the ingestion from processing entirely, so S3 doesn't block on downstream success.

- **`SqsEventSource`** creates an `AWS::Lambda::EventSourceMapping` that configures Lambda to poll the SQS queue. Key parameters available on the source:
  ```python
  lambda_event_source.SqsEventSource(
      queue,
      batch_size=10,                      # records per invocation
      max_batching_window=Duration.seconds(10),
      report_batch_item_failures=True,    # return partial failures
  )
  ```
  The event source mapping handles polling, batching, and scaling. Lambda scales up by adding more pollers when the queue has visible messages.

- **DLQ at SQS level** catches messages that Lambda repeatedly fails to process. After the consumer receives a message `max_receive_count` times and the visibility timeout expires each time, the message moves to the DLQ. This is distinct from a subscription-level DLQ — it protects against Lambda-side processing failures, not delivery failures.

- **Lambda batch processing:** The Lambda handler receives an `event` dict with an `event["Records"]` array. Each record has `body` (the SQS message body), `messageId`, `receiptHandle`, and `attributes`. For S3 events, the body is a JSON string containing the S3 event notification (bucket name, object key, size, etc.). The function must delete the message after processing — Lambda does this automatically on success (no error thrown). On failure, the message remains in the queue for retry.

- **CDK grants** generate IAM policies without raw policy documents:
  - `queue.grant_consume_messages(processor)` — adds `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`, `sqs:GetQueueUrl` to the Lambda's execution role
  - `input_bucket.grant_read(processor)` — adds `s3:GetObject` and `s3:ListBucket` (for the bucket specified)
  - `table.grant_write(processor)` — adds `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:DeleteItem` (and `dynamodb:BatchWriteItem`)

- **This pattern decouples ingestion from processing:** S3 publishes events to SQS without waiting. SQS absorbs traffic spikes by buffering messages. Lambda consumes at its own pace. If Lambda is down or scaling, messages stay in SQS until processing resumes. The queue acts as a shock absorber between a bursty producer (S3 uploads) and a processing function that may not scale instantly.

### Key CDK Concepts

- `s3n.SqsDestination(queue)` is a `Destination` class that grants S3 `sqs:SendMessage` and creates the notification configuration on the bucket. It does NOT require a separate queue policy — the grant is handled transparently.
- `lambda_event_source.SqsEventSource(queue).bind(processor)` is the explicit wiring form. An alternative shorthand: `processor.add_event_source(lambda_event_source.SqsEventSource(queue))` — both produce the same `EventSourceMapping`.
- `sqs.DeadLetterQueue` is a struct that CDK serializes to `RedrivePolicy` JSON on the queue. The DLQ itself must be a separate `sqs.Queue` construct.
- The Lambda function's `code` shown is inline for brevity; in production, use `Code.from_asset("path/to/handler")` with dependencies managed via `requirements.txt` or `PythonFunction`.
- `BillingMode.PAY_PER_REQUEST` on the DynamoDB table avoids capacity planning — useful for spiky S3 processing workloads.

## Cross-Refs

See [[s3-event-notifications]] for detailed S3 notification configuration options.
See [[sqs-queue-patterns]] for DLQ setup, visibility timeout, and FIFO alternatives.
See [[dynamodb-basics]] for DynamoDB table configuration and key schema design.
See [[lambda-s3-integration]] for direct S3→Lambda integration (without a queue).
