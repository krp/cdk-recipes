---
tags:
  - foundation
---

# Environment Context

Account, region, stage, and deployment environment — how to make your CDK app environment-aware.

## Code

```python
from aws_cdk import App, Aws, Environment, Stack

class MyStack(Stack):
    def __init__(self, scope, id, *, stage, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.stage = stage

        # Conditional resource — production gets encrypted, others don't
        if stage == "prod":
            from aws_cdk import aws_s3 as s3
            s3.Bucket(self, "Data", encryption=s3.BucketEncryption.KMS)

        # Tokens — resolved at deploy time
        print(f"Account: {Aws.ACCOUNT_ID}, Region: {Aws.REGION}")

app = App()
MyStack(app, "DevStack", stage="dev",
    env=Environment(account="111111111111", region="us-west-2"))
MyStack(app, "ProdStack", stage="prod",
    env=Environment(account="222222222222", region="us-east-1"))
```

## What's Happening

The `env` property on a `Stack` binds it to a specific AWS account and region. This matters for two reasons:

1. **Context provider lookups** — stacks that use VPC lookups, AZ lookups, or SSM parameters need a resolved environment so CDK knows which account and region to query.
2. **Cross-stack references** — exporting and importing stack outputs requires knowing the target account/region for `Fn::ImportValue` resolution.

### `env` vs Token Attributes

When you specify `env=Environment(account="123456", region="us-east-1")`, the account and region are **concrete** — CDK knows them at synthesis time. When you use `Aws.ACCOUNT_ID` or `Aws.REGION`, you get **tokens** that CloudFormation resolves at deploy time.

Tokens are flexible (the same template works in any account) but opaque — CDK cannot use the value during synthesis. Concrete env values enable lookups but pin the stack to one account/region.

### Partition Awareness

CDK provides `Aws.PARTITION` — a token that resolves to `"aws"`, `"aws-cn"`, or `"aws-us-gov"` at deploy time. Use it when constructing ARNs or policies that need to work across partitions:

```python
from aws_cdk import Aws
# Aws.PARTITION → "aws" in commercial, "aws-cn" in China, "aws-us-gov" in GovCloud
```

### Stage-Based Configuration

Pass a `stage` string (or an enum) to the stack constructor and use it to conditionally configure resources. This pattern keeps configuration explicit in the `app.py` entry point rather than buried in context lookups:

```python
# app.py
prod_stack = MyStack(app, "ProdStack", stage="prod",
    env=Environment(account="222222222222", region="us-east-1"))
dev_stack = MyStack(app, "DevStack", stage="dev",
    env=Environment(account="111111111111", region="us-west-2"))
```

Combine with context (see [[stack-parameters-and-context]]) to load stage-specific values from `cdk.json` or SSM Parameter Store.

See [[stack-parameters-and-context]] for the full context mechanism, and [[multi-account-deployments]] for managing environment-specific pipelines.
