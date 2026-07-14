---
tags: testing, security, advanced
---

# CDK Nag Compliance

Automated compliance checking against AWS best practice rule packs using cdk-nag.

## Code

```python
from cdk_nag import NagSuppressions, AwsSolutionsChecks

app = App()
stack = MyStack(app, "MyStack")

# Apply the AwsSolutions rule pack as an Aspect
cdk.Aspects.of(stack).add(AwsSolutionsChecks())

# Suppress a specific rule for a named resource
NagSuppressions.add_stack_suppressions(stack, [
    {
        "id": "AwsSolutions-S1",
        "reason": "Access logs not required for dev buckets",
        "applies_to": ["BucketName::DevBucket"],
    }
])

app.synth()
```

## What's Happening

- `cdk-nag` is a third-party library implemented as an Aspect — it visits every construct in the tree and checks the synthesized resource against rule packs
- Rule packs available: `AwsSolutionsChecks` (AWS solutions), `HIPAASecurityChecks` (HIPAA), `NIST80053Checks` (NIST 800-53), `PCIDSSChecks` (PCI DSS)
- `AwsSolutionsChecks()` is added via `cdk.Aspects.of(stack).add()` — the Aspect framework calls `visit()` on each construct, and cdk-nag evaluates rules against the synthesized L1 properties
- Suppressions: `NagSuppressions.add_stack_suppressions()` applies to the entire stack; `add_resource_suppressions()` targets a specific construct path. Each suppression requires a `reason` explaining why the rule does not apply
- `applies_to` scopes suppression to resources matching specific values (e.g., bucket name, Lambda function ID, SQS queue URL) — suppress only the known exceptions, not the entire rule
- cdk-nag blocks `cdk synth` on violations (exit code 1 with error messages) unless suppressed — this makes it effective in CI/CD pipelines where a failing synth prevents deployment
- Integration: add to a pipeline stage's `post` step or to a checks-only synth step that gates deployment; pre-suppressed rules remain suppressed, new violations fail the build

### Key CDK Concepts

- cdk-nag uses the Aspect pattern to walk the construct tree — the same mechanism used for permission boundaries (see [[permission-boundaries]]) and other cross-cutting concerns
- Rule checks are evaluated during synthesis because Aspects run before template output — violations surface as synthesis errors, not runtime failures
- The `applies_to` filter inspects resource-level properties at synthesis time; it supports patterns like `"BucketName::*dev*"` for wildcard matching

Cross-ref: [[testing-with-assertions]], [[advanced-aspects]], [[cicd-pipeline]]
