---
tags: monitoring
---

# CloudWatch Metric, Alarm with SNS Action, and Composite Alarms

A CloudWatch metric constructed from an SQS queue (via CDK's metric factory pattern), an alarm that triggers an SNS action, and a composite alarm combining multiple alarms with boolean logic.

## Code

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sqs as sqs,
    aws_sns as sns,
)
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        queue = sqs.Queue(self, "Orders")
        alarm_topic = sns.Topic(self, "AlarmTopic")

        # Metric factory — pre-fills namespace, metric name, and dimensions
        metric = queue.metric_approximate_age_of_oldest_message(
            statistic="Max",
            period=Duration.minutes(5),
        )

        alarm = cw.Alarm(
            self,
            "OldMessageAlarm",
            metric=metric,
            threshold=300,  # 5 minutes
            evaluation_periods=2,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # Composite alarm — combines multiple alarms with boolean operators
        composite = cw.CompositeAlarm(
            self,
            "ProdComposite",
            alarm_rule=cw.AlarmRule.any_of(
                alarm,
                cw.AlarmRule.from_other_alarm(cpu_alarm, cw.AlarmState.ALARM),
            ),
        )
```

## What's Happening

- **`queue.metric_*()` methods** return `Metric` objects with the namespace, metric name, and dimensions pre-filled from the queue construct. Every CDK resource that emits CloudWatch metrics exposes a metric factory — this is CDK's alternative to manually constructing `Metric` dicts with `namespace` and `dimensions`.

- **`Metric` objects are reusable:** a `Metric` can be passed to `Alarm`, dashboard widgets (`GraphWidget`, `SingleValueWidget`), or exported as a stack output without re-specifying the metric identity.

- **`Alarm` (L2)** wraps `CfnAlarm` with typed properties for comparison operators, missing data treatment, and alarm actions. The `treat_missing_data` parameter controls behavior during metric gaps — `NOT_BREACHING` prevents false alarms during deployments or brief metric interruptions.

- **`add_alarm_action()` vs `add_ok_action()` vs `add_insufficient_data_action()`**: CDK generates the `AlarmActions`, `OKActions`, and `InsufficientDataActions` CloudFormation arrays. Each method can be called multiple times; CDK appends to the list.

- **`CompositeAlarm`** is CDK's L2 for `CfnCompositeAlarm`. It combines existing alarms with `AlarmRule` boolean operators (`any_of`, `all_of`, `not`). Composite alarms have their own state that depends on the child alarms — they don't publish their own metrics.

- **`AlarmRule.from_other_alarm()`** creates a rule condition referencing another alarm by ARN. The referenced alarm (`cpu_alarm`) must exist in the same stack or be a cross-stack reference.

### Key CDK Concepts

- `Metric` is a CDK struct (not a CloudFormation resource) — it describes *what* to measure. During synthesis it serializes into the alarm's `Metric` JSON or the dashboard's `Metrics` array.
- `cw.Alarm` is an L2 construct that creates `AWS::CloudWatch::Alarm`. The metric is embedded in the alarm resource; there is no standalone metric resource.
- `cw_actions.SnsAction` implements `IAlarmAction`. During synthesis it returns the `ARN` of the SNS topic as the alarm action — no additional resources are created.
- `CompositeAlarm` creates `AWS::CloudWatch::CompositeAlarm`. Child alarms must already exist; CDK synthesizes the `AlarmRule` string from the `AlarmRule` expression tree.
- Cross-stack alarm references work via CDK tokens — `CompositeAlarm` in Stack A can reference an alarm in Stack B as long as the ARN is exported/imported.

## Cross-Refs

See [[dashboards]] for placing these metrics and alarms on a CloudWatch dashboard.
See [[sns-topic-subscriptions]] for subscription types and DLQ configuration on the alarm topic.
