---
tags: storage, event-driven
---

# S3 Event Notifications to SQS, SNS, and Lambda

Trigger asynchronous workflows by publishing S3 bucket events (object created, deleted, restored) to SQS queues, SNS topics, or Lambda functions — with server-side prefix/suffix filtering.

## Code

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as lambda_,
)
from constructs import Construct


class EventBridgeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(self, "SourceBucket", versioned=True)

        # SQS — fan out events to one or more consumers
        queue = sqs.Queue(self, "ImageQueue", visibility_timeout=Duration.seconds(300))
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(queue),
            s3.NotificationKeyFilter(prefix="images/", suffix=".jpg"),
        )

        # SNS — publish to subscribers (email, HTTP, Lambda, etc.)
        topic = sns.Topic(self, "ImageTopic")
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(topic),
            s3.NotificationKeyFilter(prefix="images/", suffix=".jpg"),
        )

        # Lambda — process objects inline
        processor = lambda_.Function(
            self,
            "ImageProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset("./src"),
        )
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor),
            s3.NotificationKeyFilter(prefix="images/", suffix=".jpg"),
        )
```

## What's Happening

- **`add_event_notification`** is a convenience method on the `Bucket` L2 construct. It does three things in a single call: (1) grants the S3 service principal permission to invoke the target (e.g., `sqs:SendMessage`, `sns:Publish`, `lambda:InvokeFunction`), (2) creates the `AWS::S3::Bucket` notification configuration on the bucket, and (3) when the target exists in the same stack, adds the necessary `DependsOn` to ensure the target is created before S3 tries to deliver to it.

- **The `Destination` classes** (`SqsDestination`, `SnsDestination`, `LambdaDestination`) encapsulate the permission grants and notification configuration. Each knows which IAM statement to add to the target's resource policy and how to format the CloudFormation notification configuration. Using them is preferred over raw `CfnBucket` notification configuration because they handle cross-stack permissions correctly.

- **At-least-once delivery:** S3 event notifications are delivered at least once, meaning consumers must be idempotent. Duplicate events can occur due to retries or replication. Use idempotency keys in the event payload (the `eventName`, `bucket.name`, and `object.key` combination is usually sufficient) and design consumers to handle the same event arriving more than once.

- **Server-side filtering** via `NotificationKeyFilter(prefix=..., suffix=...)` is evaluated by S3 before the notification is sent. Events that don't match the filter are never transmitted — there is no cost for filtered-out events and no load on the consumer. This is more efficient than filtering in the consumer after delivery.

### Key CDK Concepts

- The `s3n.LambdaDestination` also attaches `AWS::Lambda::Permission` to allow S3 to invoke the function — you don't need a separate `add_permission` call.
- Notification configurations on a bucket are limited to 100 total (across all event types). Each distinct filter combination counts as one configuration.
- S3 notifications support these event types: `OBJECT_CREATED` (all PUT/POST/COPY/MultipartUpload), `OBJECT_REMOVED`, `OBJECT_RESTORE_POST`, `OBJECT_RESTORE_COMPLETED`, `REDUCED_REDUNDANCY_LOST_OBJECT`, `REPLICATION_OPERATION_FAILED_REPLICATION`, `REPLICATION_OPERATION_MISSED_SCOPE`, `REPLICATION_OPERATION_REPLICATION_NOT_TRACKED`, `LIFECYCLE_EXPIRATION_*`, and `INTELLIGENT_TIERING`.
- `versioned=True` on the bucket does not change notification behavior — versioned and non-versioned buckets deliver the same event payload shape.

## Cross-Refs

See [[sqs-queue-patterns]] for dead-letter queues and queue configuration.
See [[sns-topic-subscriptions]] for SNS subscriber patterns (SQS, email, HTTP).
See [[lambda-s3-integration]] for Lambda error handling and retry configurations.
See [[async-pipeline-s3-sqs-lambda-ddb]] for the full end-to-end pattern.
