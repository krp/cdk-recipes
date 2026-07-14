---
tags:
  - event-driven
  - messaging
---

# SNS Topic with Multiple Subscription Types and DLQ

An SNS topic configured with multiple subscription destinations (SQS queue, Lambda function, email) and a dead-letter queue at the subscription level for undeliverable messages.

## Code

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sqs as sqs,
    aws_lambda as lambda_,
)
from constructs import Construct


class TopicStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # SNS topic — non-FIFO for multi-subscriber fanout
        topic = sns.Topic(self, "MyTopic", fifo=False)

        # DLQ for failed SQS delivery attempts
        queue_dlq = sqs.Queue(self, "TopicDLQ")

        # Main subscriber queue with redrive through the DLQ
        queue = sqs.Queue(
            self,
            "SubQueue",
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=queue_dlq,
            ),
        )
        topic.add_subscription(sns_subscriptions.SqsSubscription(queue))

        # Lambda subscription
        processor_fn = lambda_.Function(
            self,
            "Processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    print("received:", event)\n'
            ),
        )
        topic.add_subscription(sns_subscriptions.LambdaSubscription(processor_fn))

        # Email subscription — for human alerting only
        topic.add_subscription(sns_subscriptions.EmailSubscription("ops@example.com"))
```

## What's Happening

- **`add_subscription`** auto-creates the subscription resource (`AWS::SNS::Subscription`) and grants the necessary publish permissions. For SQS it adds a queue policy allowing `sns:Publish`, for Lambda it adds a resource-based policy allowing SNS to invoke the function, and for email it generates a subscription confirmation request.

- **`SqsSubscription`, `LambdaSubscription`, `EmailSubscription`** are CDK `Subscription` classes that encapsulate the target-specific resource policy. Each class knows which IAM statements to add and how to format the subscription configuration. A raw `CfnSubscription` would require manually wiring the permissions.

- **SNS → SQS:** CDK adds a queue policy statement granting `sns:Publish` from the topic's ARN. Without it, SNS would fail to deliver to the queue despite the subscription existing.

- **SNS → Lambda:** CDK calls `add_permission` on the Lambda function to allow the SNS service principal (`sns.amazonaws.com`) to invoke it. The subscription ARN is included in the `SourceArn` condition so only this specific topic can trigger the function.

- **DLQ at subscription level:** The `DeadLetterQueue` struct on the subscriber queue captures messages that SNS cannot deliver — for example, when the Lambda subscription throttles or the SQS queue rejects due to exceeding the `max_receive_count`. The DLQ at the subscription level is distinct from the SQS queue's own DLQ: this one catches SNS delivery failures, while the SQS DLQ catches downstream processing failures.

- **Filter policies** can be added to any subscription to perform content-based filtering before delivery:
  ```python
  topic.add_subscription(
      sns_subscriptions.SqsSubscription(
          queue,
          filter_policy={
              "event": sns.SubscriptionFilter.string_filter(
                  allowlist=["order_placed", "order_shipped"],
              ),
              "priority": sns.SubscriptionFilter.numeric_filter(
                  greater_than=5,
              ),
          },
      )
  )
  ```
  Only messages whose attributes match the filter policy are delivered. Non-matching messages are dropped (not sent to the DLQ).

- **FIFO topics** (`fifo=True`) require FIFO queues as subscribers and enforce message ordering and deduplication. Only one subscription type supports FIFO: SQS. Lambda and email subscriptions are not compatible with FIFO topics.

### Key CDK Concepts

- `sns.Topic` is an L2 construct that wraps `AWS::SNS::Topic`. Setting `fifo=False` is the default and is shown explicitly for clarity.
- The `Subscription` classes are not full L2 constructs — they implement `ITopicSubscription` and are consumed by the topic's `add_subscription` method. The topic construct manages the lifecycle.
- Queue DLQ at subscription level: the `dead_letter_queue` property on the subscriber *queue* uses `sqs.DeadLetterQueue` (a struct, not a construct). CDK generates the `RedrivePolicy` JSON on the queue resource.
- `EmailSubscription` requires manual confirmation — AWS sends a confirmation email to the address before the subscription becomes active.

## Cross-Refs

See [[sqs-queue-patterns]] for queue configuration and DLQ setup.
See [[eventbridge-custom-bus]] to compare SNS fanout vs EventBridge event routing.
See [[async-pipeline-s3-sqs-lambda-ddb]] for a complete async pipeline pattern.
