---
tags:
  - foundation
---

# Multiple Stacks

Multiple stacks in one CDK app, sharing resources via stack properties.

## Code

```python
from aws_cdk import App, Stack
from aws_cdk import aws_ec2 as ec2

class VpcStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.vpc = ec2.Vpc(self, "Vpc", max_azs=2)

class AppStack(Stack):
    def __init__(self, scope, id, *, vpc: ec2.IVpc, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Use the shared VPC
        ec2.SecurityGroup(self, "AppSg", vpc=vpc)

app = App()
vpc_stack = VpcStack(app, "VpcStack")
AppStack(app, "AppStack", vpc=vpc_stack.vpc)
app.synth()
```

## What's Happening

CDK stacks map 1:1 to CloudFormation stacks. When you pass an `IVpc` reference from one stack to another, CDK generates an **export** in the source stack (`Fn::Export`) and an **import** in the consuming stack (`Fn::ImportValue`). The synthesized templates are independent but connected via CloudFormation cross-stack references.

### Stack Dependencies

CDK automatically builds a dependency graph from cross-stack references: `AppStack` depends on `VpcStack` because it uses `vpc_stack.vpc`. During deployment, CDK deploys `VpcStack` first, then `AppStack`. You can also add explicit dependencies with `stack.node.add_dependency(other)`.

### When to Use Multiple Stacks

- **Independent lifecycle**: resources that are updated or deleted on different schedules
- **Environment isolation**: separate stacks for VPC, data plane, and application so a failed application deployment doesn't affect networking
- **CloudFormation limits**: a single stack caps at 200 outputs and 500 resources. Multiple stacks let you scale past these limits
- **IAM permission boundaries**: different stacks may require different deployment roles

### Multiple Stacks vs Nested Stacks

| Multiple stacks | Nested stacks |
|----------------|---------------|
| Independent CloudFormation stacks | Single parent stack includes sub-templates |
| Cross-stack references use `Fn::ImportValue` / `Export` | References stay within the parent via `Fn::GetAtt` |
| Each stack is deployed separately | Deployed as one unit |
| Stacks can be in different accounts/regions | All nested stacks deploy to the same account/region |
| Useful for separation of concerns | Useful for grouping related resources under one lifecycle |

### Limits

A single CloudFormation stack supports:
- 200 outputs
- 500 resources
- 60 parameter entries

When you approach these limits, split the stack. Prefix the stack name consistently (e.g. `DataStack`, `NetworkStack`, `AppStack`) so the deployment order is clear.

See [[nested-stacks]] for the alternative grouping strategy, and [[hello-cdk]] for the minimal app scaffold.
