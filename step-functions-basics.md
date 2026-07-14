---
tags: step-functions, compute
---

# Step Functions Basics

CDK's L2 `aws_stepfunctions` module models state machines through a `Chain`-based DAG builder and typed state constructs. The entire definition is synthesized into a CloudFormation `DefinitionString` JSON.

## Code

```python
from aws_cdk import Duration
from aws_cdk import aws_stepfunctions as sfn

pass_state = sfn.Pass(self, "Hello", result=sfn.Result.from_object({"message": "Hello"}))
wait_state = sfn.Wait(self, "WaitForProcessing", time=sfn.WaitTime.duration(Duration.seconds(30)))

machine = sfn.StateMachine(
    self, "MyMachine",
    definition=pass_state.next(
        wait_state
    ).next(
        sfn.Succeed(self, "Done")
    ),
    state_machine_type=sfn.StateMachineType.STANDARD,
)
```

With `Choice` and `Map`:

```python
# Choice branches on a condition
choice = sfn.Choice(self, "CheckStatus")
approved = sfn.Pass(self, "Approved")
denied = sfn.Pass(self, "Denied")

choice.when(sfn.Condition.string_equals("$.status", "approved"), approved)
choice.otherwise(denied)

# Map iterates over an array — each element processed by a sub-chain
map_state = sfn.Map(self, "ProcessItems",
    max_concurrency=5,
    items_path=sfn.JsonPath.string_at("$.items"),
)
map_state.item_processor(
    sfn.Pass(self, "Transform").next(
        tasks.LambdaInvoke(self, "Save", lambda_function=save_fn)
    )
)
```

## What's Happening

- `.next()` is a `Chain` method — it returns a new `Chain` node, enabling fluent DAG construction. CDK generates the `DefinitionString` JSON at synthesis time, including ARN references for Lambda functions and other resources.
- `sfn.Pass`, `sfn.Wait`, `sfn.Succeed`, `sfn.Fail` are L2 state constructs. `Pass` injects or transforms data without invoking a service; `Wait` pauses execution; `Succeed`/`Fail` are terminal states.
- `sfn.Result` and `sfn.JsonPath` provide typed helpers for manipulating state data and paths. `sfn.Result.from_object()` creates a static JSON result; `sfn.JsonPath.string_at("$.path")` resolves a JSONPath expression from the execution data.
- `Choice` with `.when(condition, target)` adds a `Choice` rule — CDK generates the `Choices` array and `Default` target. `Condition` exposes static factory methods: `string_equals`, `numeric_greater_than`, `boolean_equals`, etc.
- `Map` with `.item_processor(chain)` generates a `Map` state that runs the sub-chain for each element in the input array. The sub-chain is a self-contained `Chain` — it can branch, retry, and reference other states.
- `StateMachineType.STANDARD` produces an exactly-once, long-running workflow (up to 1 year). `EXPRESS` is at-least-once, faster, and cheaper but capped at 5 minutes.

### Key CDK Concepts

- The `definition` property accepts a `Chain` object — it is an L2 abstraction. The `definition_body` and `definition_substitutions` properties on `StateMachine` allow escape-hatch overrides for dynamic `DefinitionString` injection.
- `sfn.JsonPath` methods return CDK tokens that resolve during synthesis; they are not runtime Python values. Use them anywhere a JSONPath string is needed in the state machine definition.
- `StateMachine` auto-generates an IAM role with `states:StartExecution` and linked service permissions (e.g., `lambda:InvokeFunction` for task states within the definition).

Cross-ref: [[step-functions-lambda-chain]], [[step-functions-callback]], [[eventbridge-custom-bus]]
