---
tags:
  - security
  - advanced
---

# Permission Boundaries

Apply IAM permission boundaries to all roles in a CDK app to prevent privilege escalation.

## Code

```python
# Via Aspect — visits every construct and patches L1 roles
class PermissionBoundaryAspect:
    def visit(self, node):
        if isinstance(node, iam.Role):
            core.CfnResource(node.node.default_child).add_property_override(
                "PermissionsBoundary",
                "arn:aws:iam::123456:policy/boundary-policy"
            )

app = App()
app.node.apply_aspect(PermissionBoundaryAspect())

# Stack-level usage — boundary is applied by the Aspect to every role
class BoundedStack(Stack):
    def __init__(self, scope, id, *, permissions_boundary_arn, **kwargs):
        super().__init__(scope, id, **kwargs)
        iam.Role(self, "AppRole", ...)
```

## What's Happening

- Permission boundaries limit the maximum permissions a role can receive — enforced at the AWS account level regardless of the policy attached to the role
- CDK's `iam.Role` L2 does not expose a `permissions_boundary` property at the time of writing — the escape hatch (Aspects or L1 overrides) is the standard approach
- `Aspect.visit()` is called for every construct in the tree; checking `isinstance(node, iam.Role)` targets only role constructs, and `.node.default_child` gets the underlying `CfnRole` L1 where the property override is applied
- Alternative approaches: use `CfnRole` directly instead of `iam.Role`, or override the synthesized template with `CfnInclude`
- `cdk bootstrap --custom-permissions-boundary` sets the boundary for the CDK deployment role itself (the role CloudFormation assumes), not for application roles
- Without boundaries, any developer who can deploy CDK stacks can create roles with any permissions, including escalating to admin — boundaries enforce a maximum ceiling

### Key CDK Concepts

- `Aspect` is a CDK mechanism to apply cross-cutting logic across the entire construct tree — visit order is pre-order (parent before children)
- `.node.default_child` is the L1 `CfnResource` that the L2 construct wraps; mutations on it affect the synthesized CloudFormation directly via property overrides
- `add_property_override` modifies the template at synthesis time — the override path matches the CloudFormation resource schema key

Cross-ref: [[iam-roles-and-grants]], [[advanced-aspects]], [[multi-account-deployments]]
