---
tags: step-functions, compute
---

# Step Functions Lambda Chain

Chaining Lambda invocations with CDK's `LambdaInvoke` task. Each task generates a `Task` state configured with the Lambda integration ARN and automatic IAM permissions.

## Code

```python
from aws_cdk import Duration
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks

task1 = tasks.LambdaInvoke(self, "ValidateOrder", lambda_function=validate_fn)
task2 = tasks.LambdaInvoke(self, "ProcessPayment", lambda_function=payment_fn)
task3 = tasks.LambdaInvoke(self, "FulfillOrder", lambda_function=fulfill_fn)

machine = sfn.StateMachine(
    self, "OrderWorkflow",
    definition=task1.next(task2.next(task3)),
)
```

With error handling and result selection:

```python
task = tasks.LambdaInvoke(
    self, "Process",
    lambda_function=fn,
    retry_on_service_exceptions=True,
    result_path="$.result",
    result_selector={
        "status": sfn.JsonPath.string_at("$.Payload.status"),
        "transaction_id": sfn.JsonPath.string_at("$.Payload.txn_id"),
    },
).add_retry(
    errors=[sfn.Errors.ALL],
    max_attempts=2,
    interval=Duration.seconds(5),
).add_catch(
    sfn.Pass(self, "Recovery", result=sfn.Result.from_object({"state": "fallback"})),
    errors=[sfn.Errors.ALL],
)
```

Controlling payload input:

```python
# Static payload
tasks.LambdaInvoke(self, "Notify", lambda_function=notify_fn,
    payload=sfn.TaskInput.from_object({"source": "order-service", "action": "confirm"}),
)

# Dynamic payload — extract from execution data
tasks.LambdaInvoke(self, "Notify", lambda_function=notify_fn,
    payload=sfn.TaskInput.from_json_path_at("$.order"),
)
```

## What's Happening

- `LambdaInvoke` is an L2 `Task` construct — it generates a `Task` state with `"Resource": "arn:aws:states:::lambda:invoke"` and `"Parameters"` containing the Lambda function ARN. CDK also synthesizes the `Lambda:InvokeFunction` IAM permission on the state machine role via `lambda_function.grant_invoke()`.
- `result_path` controls where the Lambda's response (the full `LambdaInvoke` output envelope, including `ExecutedVersion`, `StatusCode`, and `Payload`) is placed in the execution data. Default `"$"` overwrites the entire execution data; `"$.result"` nests it under a key; `null` discards the output.
- `result_selector` extracts specific fields from the Lambda response using `sfn.JsonPath.string_at(...)` — CDK generates `ResultSelector` on the Task state. This avoids passing the full Lambda envelope downstream.
- `add_retry` adds a `Retry` field to the Task state. `sfn.Errors.ALL` catches every error type; `max_attempts` and `interval` control backoff. `retry_on_service_exceptions=True` (a convenience shorthand) only retries `States.TaskFailed`.
- `add_catch` adds a `Catch` field — if the task fails after retries are exhausted, execution transitions to the specified fallback state. The fallback state receives the error details in its input.
- `sfn.TaskInput.from_object(...)` generates a static JSON payload. `sfn.TaskInput.from_json_path_at(...)` resolves a JSONPath at runtime, forwarding a portion of the execution data to the Lambda.

### Key CDK Concepts

- `LambdaInvoke` is a `TaskStateBase` subclass. Any `TaskStateBase` supports `add_retry`, `add_catch`, `result_path`, `result_selector`, and `integration_pattern`.
- IAM grants are automatic: `LambdaInvoke` captures the `lambda_function` reference and calls `grant_invoke` during synthesis. No manual role policy needed.
- The `payload` property of `LambdaInvoke` maps to the Task state's `Parameters` — static values become literal JSON, `JsonPath` arguments become `.$`-suffixed template strings in the synthesized definition.

Cross-ref: [[step-functions-basics]], [[lambda-hello-python]]
