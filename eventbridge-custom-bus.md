---
tags: event-driven, messaging
---

# Custom EventBridge Bus with Rules, Content Filtering, Archive, and Replay

A custom EventBridge event bus with a content-filtered rule targeting a Lambda function, plus an archive for event retention and replay.

## Code

```python
import json
from aws_cdk import (
    Stack,
    Duration,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
)
from constructs import Construct


class BusStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        processor_fn = lambda_.Function(
            self,
            "Processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    print("processed:", event)\n'
            ),
        )

        # Custom event bus — isolates event domains from the default bus
        bus = events.EventBus(
            self,
            "AppBus",
            event_bus_name="app-bus",
        )

        # Rule with content-based filtering
        rule = events.Rule(
            self,
            "OrderPlaced",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=["app.orders"],
                detail_type=["OrderPlaced"],
                detail={
                    "amount": events.Match.greater_than(100),
                },
            ),
        )
        rule.add_target(targets.LambdaFunction(processor_fn))

        # Archive — stores matching events for later replay
        archive = bus.archive(
            "OrderArchive",
            event_pattern=events.EventPattern(
                source=["app.orders"],
            ),
            retention=Duration.days(7),
        )
```

## What's Happening

- **Custom bus vs default bus:** The `default` event bus receives events from AWS services (EC2 state changes, CodePipeline status, etc.). A custom bus (`event_bus_name="app-bus"`) isolates application-specific events. Events published to one bus are never visible on another. Rules on a custom bus only match events sent to that bus.

- **`EventPattern`** is a CDK class that serializes into the CloudFormation `EventPattern` JSON. The structure mirrors the EventBridge event envelope: `source`, `detail-type` (`detail_type` in Python), `resources`, `region`, `account`, and `detail` (the application-specific payload). CDK validates the pattern during synthesis — non-existent keys are not caught at synthesis, but malformed comparisons (e.g., a string where a number is expected) fail at deploy time.

- **`Match` class** provides typed helpers that generate the correct EventBridge comparison expression:
  - `Match.equals(...)` — exact value match (the default when you pass a raw string)
  - `Match.greater_than(100)` — numeric comparisons
  - `Match.exists` — field must be present
  - `Match.anything_but("value")` / `Match.anything_but(prefix="...")` — negative matching
  - `Match.prefix("orders-")` — prefix matching on strings
  - `Match.numeric(...)` — range comparisons (`less_than`, `less_or_equal`, `greater_than`, `greater_or_equal`)
  - `Match.cidr("10.0.0.0/8")` — IP address range matching
  - `Match.exact_string("...")` — for `detail_type` and `source` when you need explicit string matching

  Without `Match`, passing a raw value like `"OrderPlaced"` to `detail_type` is equivalent to `Match.equals("OrderPlaced")`.

- **`Archive`** is created from the bus construct via `bus.archive(...)`. It captures events matching the archive's own `event_pattern` and stores them for the specified retention period. The archive is independent of rules — events can be archived regardless of whether any rule matches. Archives are cheap storage (per-event pricing) and are the prerequisite for replays.

- **Replay** requires an archive and a target time range. It redelivers events from the archive to the same bus (not directly to a target):
  ```python
  # Replay requires CfnReplay — no L2 construct yet
  from aws_cdk import aws_events as events

  events.CfnArchive(
      self, "AppArchive",
      source_arn=bus.event_bus_arn,
      archive_name="app-bus-archive",
      retention_days=7,
  )

  events.CfnReplay(
      self, "OrderReplay",
      replay_name="replay-orders",
      event_source_arn=bus.event_bus_arn,
      destination={
          "arn": bus.event_bus_arn,
      },
      time_period={
          "start": "2024-01-01T00:00:00Z",
          "end": "2024-01-02T00:00:00Z",
      },
  )
  ```

- **Targets** are added via `rule.add_target(...)`. The `aws_events_targets` module (`targets`) provides:
  - `targets.LambdaFunction(fn)` — CDK auto-adds `lambda:InvokeFunction` permission
  - `targets.SqsQueue(queue)` — CDK grants `sqs:SendMessage`
  - `targets.SnsTopic(topic)` — CDK grants `sns:Publish`
  - `targets.SfnStateMachine(sm)` — CDK grants `states:StartExecution`
  - `targets.ApiGateway(restApi)` — CDK grants `execute-api:Invoke`
  Each target class handles the permission wiring automatically.

- **Input transformation** can modify the event before delivery:
  ```python
  rule.add_target(
      targets.LambdaFunction(
          processor_fn,
          event=events.RuleTargetInput.from_event_path("$.detail"),
      )
  )
  ```

### Key CDK Concepts

- `events.EventBus` is an L2 construct. When `event_bus_name` is given, CDK creates a `AWS::Events::EventBus` resource. Omit it to reference the default bus (no resource created).
- `events.Rule` with `event_bus=bus` attaches the rule to the custom bus. Without `event_bus`, the rule attaches to the default bus.
- The `archive` method on the bus construct returns an `Archive` object whose `archive_name` and `archive_arn` properties are CDK tokens.
- `events.Match` methods are syntax helpers that produce CloudFormation-compatible event pattern dicts. They have no runtime effect.

## Cross-Refs

See [[eventbridge-scheduler]] for time-based scheduling (not event-driven rules).
See [[sns-topic-subscriptions]] to compare SNS fanout vs EventBridge content-based routing.
See [[step-functions-lambda-chain]] for orchestrating workflows triggered by EventBridge.
