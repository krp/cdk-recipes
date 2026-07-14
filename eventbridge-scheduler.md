---
tags: event-driven, compute
---

# EventBridge Scheduler — Cron and Rate Triggers for Lambda

Schedule a Lambda function invocation on a cron or rate expression using EventBridge Scheduler, with flexible time windows and an explicit IAM role for the scheduler to invoke the target.

## Code

```python
from aws_cdk import (
    Stack,
    aws_scheduler as scheduler,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct


class SchedulerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_.Function(
            self,
            "TargetFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    print("scheduled run:", event)\n'
            ),
        )

        schedule_group = scheduler.ScheduleGroup(self, "Group")

        # IAM role that Scheduler assumes when invoking the target
        scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        fn.grant_invoke(scheduler_role)

        scheduler.CfnSchedule(
            self,
            "NightlyTask",
            flexible_time_window={"Mode": "OFF"},
            schedule_expression="cron(0 2 * * ? *)",
            target={
                "Arn": fn.function_arn,
                "RoleArn": scheduler_role.role_arn,
            },
            group_name=schedule_group.schedule_group_name,
        )
```

## What's Happening

- **EventBridge Scheduler (`aws_scheduler`)** is a different service from EventBridge Rules (`aws_events`). Scheduler is purpose-built for scheduling — it provides one-time and recurring schedules with flexible time windows, retry policies, and dead-letter configuration. EventBridge Rules are designed for event-driven patterns (reacting to events), not scheduling. The two have separate CloudFormation resource namespaces (`AWS::Scheduler::Schedule` vs `AWS::Events::Rule`).

- **`flexible_time_window`** allows the scheduler to fire within a window around the scheduled time. `{"Mode": "OFF"}` means fire at exactly the scheduled second. Other modes: `{"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 5}` lets the scheduler delay execution up to 5 minutes, which improves throughput when many schedules fire simultaneously.

- **Schedule expressions** use the same format as CloudWatch Events: `rate(1 hour)` for simple intervals (seconds, minutes, hours, days), or `cron(0 2 * * ? *)` for complex schedules. The cron format includes six fields: minute, hour, day-of-month, month, day-of-week, year. Unlike CloudWatch Events, Scheduler also supports `at(yyyy-mm-ddThh:mm:ss)` for one-time schedules.

- **Target ARN + Role:** Scheduler requires an explicit IAM role with `iam:PassRole` permission to invoke the target. The role's trust policy must allow `scheduler.amazonaws.com` to assume it, and the role must have permission to perform the target action (e.g., `lambda:InvokeFunction`). CDK's `grant_invoke` method adds the Lambda invoke permission to the role.

- **L1 construct currently:** CDK does not have an L2 construct for EventBridge Scheduler as of 2024. `CfnSchedule` is the L1 CloudFormation resource, so you pass raw dictionary values for `target`, `flexible_time_window`, and other properties. Expect this to change when an L2 becomes available.

- **Input transformers** pass a static or dynamic payload to the target:
  ```python
  scheduler.CfnSchedule(
      self,
      "WithPayload",
      flexible_time_window={"Mode": "OFF"},
      schedule_expression="rate(1 hour)",
      target={
          "Arn": fn.function_arn,
          "RoleArn": scheduler_role.role_arn,
          "Input": json.dumps({"task": "nightly_cleanup", "env": "prod"}),
      },
      group_name=schedule_group.schedule_group_name,
  )
  ```
  Without an explicit `Input`, Scheduler sends a default event envelope. Dynamic payloads use `InputTransformer` to inject schedule attributes (e.g., `scheduled_time`).

- **A schedule group** (`ScheduleGroup`) organizes related schedules. All schedules in a group can be enabled or disabled together. If you don't specify a `group_name`, the schedule goes into the default group.

### Key CDK Concepts

- `CfnSchedule` is an L1 construct — you pass property names as raw strings matching the CloudFormation resource schema (`flexible_time_window`, `target`, `schedule_expression`, etc.). CDK does no validation of these dicts.
- The `ScheduleGroup` L2 construct exists (`scheduler.ScheduleGroup`), but schedules themselves are `CfnSchedule` L1 until the L2 ships.
- The IAM role must be created explicitly — Scheduler does not auto-generate a service-linked role for all targets. The `fn.grant_invoke(scheduler_role)` call is the CDK-idiomatic way to wire the permission.
- To use a DLQ with Scheduler, add a `DeadLetterConfig` key to the target dict pointing to an SQS queue ARN.

## Cross-Refs

See [[eventbridge-custom-bus]] for EventBridge Rules (event-driven pattern, not scheduling).
See [[lambda-hello-python]] for creating the Lambda function.
See [[iam-roles-and-grants]] for how `grant_invoke` and service principals work.
