---
tags:
  - step-functions
  - compute
  - event-driven
---

# Step Functions Callback Pattern

The `.waitForTaskToken` integration pattern pauses state machine execution until an external system sends a `send_task_success` or `send_task_failure` call with the task token. CDK models this via `IntegrationPattern.REQUIRE_TOKEN`.

## Code

```python
from aws_cdk import Duration
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks

task = tasks.LambdaInvoke(
    self, "HumanApproval",
    lambda_function=approval_fn,
    integration_pattern=sfn.IntegrationPattern.REQUIRE_TOKEN,
    task_timeout=Duration.hours(24),
)

machine = sfn.StateMachine(
    self, "ApprovalWorkflow",
    definition=task.next(sfn.Pass(self, "PostApproval")),
)
```

The Lambda receives the token in its event and must call the Step Functions API to resume execution:

```python
import json
import boto3

sfn_client = boto3.client("stepfunctions")

def handler(event, context):
    token = event["task_token"]

    if event.get("approved"):
        sfn_client.send_task_success(
            taskToken=token,
            output=json.dumps({"approved": True, "reviewed_by": event["reviewer"]}),
        )
    else:
        sfn_client.send_task_failure(
            taskToken=token,
            error="Rejected",
            cause="Human reviewer did not approve",
        )
```

Heartbeat-based timeout for stuck executions:

```python
task = tasks.LambdaInvoke(
    self, "ExternalApi",
    lambda_function=notify_fn,
    integration_pattern=sfn.IntegrationPattern.REQUIRE_TOKEN,
    heartbeat=Duration.minutes(5),       # Must receive heartbeat before this
    task_timeout=Duration.hours(2),       # Hard timeout for the whole task
)
```

## What's Happening

- `IntegrationPattern.REQUIRE_TOKEN` sets the Task state's `"Resource"` ARN to the `.waitForTaskToken` variant (e.g., `arn:aws:states:::lambda:invoke.waitForTaskToken`). CDK also grants `states:SendTaskSuccess` and `states:SendTaskFailure` on the Lambda execution role so it can call back.
- The task token is injected by Step Functions as `task_token` in the Lambda event payload. The token is an opaque string that identifies the specific state machine execution and task — it is the only way to resume the paused state.
- `send_task_success()` resumes execution with the provided `output` JSON as the task result. `send_task_failure()` terminates the execution with an error. No other API calls can resume a waiting `.waitForTaskToken` task.
- `task_timeout` sets the `Task` state's `TimeoutSeconds` — the maximum time Step Functions waits for a callback before timing out the execution. `heartbeat` sets `HeartbeatSeconds` — if no callback arrives within this window, the task fails even if the total timeout hasn't elapsed.
- Use case: human approval gates, initiating work on an external system that calls back on completion, or any long-running async process where the duration exceeds Lambda's 15-minute limit.

### Key CDK Concepts

- `IntegrationPattern` is an enum: `REQUEST_RESPONSE` (default, fire-and-forget), `RUN_JOB` (sync, .sync), and `REQUIRE_TOKEN` (callback, .waitForTaskToken). Not all services support all patterns — check the service integration documentation.
- For durable callback recovery, store the task token in DynamoDB with a TTL equal to the task timeout. A separate process can replay tokens that expired without a callback.
- The callback pattern requires the downstream service (Lambda, SQS, SNS, ECS, etc.) to have IAM permissions for `states:SendTask*`. CDK auto-grants this for `LambdaInvoke`; for other targets you must add the policy yourself.

Cross-ref: [[step-functions-lambda-chain]], [[dynamodb-basics]]
