---
tags: event-driven, messaging
---

# SQS Queue with DLQ, Redrive, Visibility Timeout, and FIFO

Standard and FIFO SQS queues with dead-letter queue configuration, redrive policy, visibility timeout, retention, and CDK grant methods for IAM permissions.

## Code

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_sqs as sqs,
)
from constructs import Construct


class QueueStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Dead-letter queue — retains failed messages for analysis
        dlq = sqs.Queue(
            self,
            "DLQ",
            retention_period=Duration.days(14),
        )

        # Standard queue with redrive to DLQ after 3 failed receives
        queue = sqs.Queue(
            self,
            "Orders",
            visibility_timeout=Duration.seconds(30),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq,
            ),
        )

        # FIFO queue — strict ordering, exactly-once processing
        fifo = sqs.Queue(
            self,
            "FifoOrders",
            fifo=True,
            content_based_deduplication=True,
        )
```

## What's Happening

- **`DeadLetterQueue`** is a CDK struct (not a construct) passed to the queue's constructor. CDK serializes it into the `RedrivePolicy` JSON on the `AWS::SQS::Queue` resource: `{"deadLetterTargetArn": <dlq-arn>, "maxReceiveCount": 3}`. The DLQ must be in the same region and account.

- **`visibility_timeout`** controls how long a message is hidden from other consumers after being received. It must be at least as long as the Lambda function timeout if the queue triggers Lambda — otherwise the function may time out processing a message while the visibility timeout expires, and a concurrent consumer receives the same message. The maximum is 12 hours (43,200 seconds).

- **FIFO queues** enforce first-in-first-out delivery and exactly-once processing. Setting `fifo=True` causes CDK to append the `.fifo` suffix to the queue name (CloudFormation enforces this). The queue must be named with `.fifo` — CDK handles this automatically from the construct ID.

- **`content_based_deduplication`** generates the deduplication ID from a SHA-256 hash of the message body, so you don't need to provide an explicit `messageDeduplicationId` per message. When disabled (the default), every `SendMessage` call must include a `MessageDeduplicationId`. Only valid on FIFO queues.

- **`retention_period`** controls how long a message lives after being sent. Minimum 60 seconds, maximum 14 days. After this period, the message is deleted regardless of whether it was consumed. The default is 4 days.

- **Grant methods** are the CDK way to grant IAM permissions on the queue:

  ```python
  # Grant a Lambda function permission to poll and delete messages
  queue.grant_consume_messages(lambda_fn)

  # Grant an application permission to send messages
  queue.grant_send_message(producer_role)

  # Grant full access (send, receive, delete, purge, get attributes)
  queue.grant(principal, "sqs:*")
  ```

  Each `grant_*` method creates an IAM policy statement attached to the principal (if it's an IAM Role construct) or returns a policy statement for manual attachment.

### Key CDK Concepts

- `sqs.Queue` is an L2 construct wrapping `AWS::SQS::Queue`. It handles the `.fifo` suffix automatically, generates `Ref` and `GetAtt` tokens for ARN, URL, and queue name.
- `DeadLetterQueue` is a plain Python dataclass (a struct). CDK converts it to CloudFormation `RedrivePolicy` at synthesis — it does not create a separate CloudFormation resource.
- The DLQ URL and ARN are accessible via `dlq.queue_url` and `dlq.queue_arn` — both are CDK tokens that resolve during deployment.
- For redrive back to the source queue (requeueing messages from the DLQ), use the AWS Console, AWS CLI `sqs-redrive-permit`, or a custom resource — CDK does not have a built-in redrive construct.

## Cross-Refs

See [[sns-topic-subscriptions]] for SNS subscriptions that deliver to SQS.
See [[async-pipeline-s3-sqs-lambda-ddb]] for the full end-to-end pipeline.
See [[iam-roles-and-grants]] for how `grant_*` methods create IAM policies.
