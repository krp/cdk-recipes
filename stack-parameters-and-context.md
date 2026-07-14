---
tags: foundation
---

# Stack Parameters and Context

Pass values into stacks at synthesis time via context variables and SSM parameters, or at deploy time via CloudFormation parameters.

## Code

```json
// cdk.json — context block
{
  "app": "python app.py",
  "context": {
    "domain": "example.com"
  }
}
```

```python
from aws_cdk import CfnParameter, Stack
from aws_cdk import aws_ssm as ssm

class ConfigStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # From cdk.json context
        domain = self.node.try_get_context("domain")
        if domain:
            print(f"Using domain: {domain}")

        # From SSM Parameter Store (synth-time lookup)
        ami_id = ssm.StringParameter.value_from_lookup(
            self, "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2"
        )

        # CloudFormation deploy-time parameter
        env_type = CfnParameter(self, "EnvType",
            type="String",
            default="dev",
            allowed_values=["dev", "stage", "prod"],
        )
```

```python
# CLI invocation
# cdk deploy --context env=prod
```

## What's Happening

CDK offers three mechanisms to inject configuration, each with a different lifecycle.

### Context (`try_get_context` / `require_get_context`)

Context is a **synthesis-time** key-value store. Values come from:
- The `context` block in `cdk.json`
- `--context` flags on the CLI
- Context provider results cached in `cdk.context.json`

`try_get_context(key)` returns `None` if the key is absent; `require_get_context(key)` raises an error. Use `try_get_context` when a default makes sense, `require_get_context` when the value is mandatory and synthesis should fail without it.

Context is resolved when `cdk synth` runs — it is not available at deploy time. Use it for values that determine *which resources* to create, not for values the resources need at runtime.

### Context Provider Pattern

`ssm.StringParameter.value_from_lookup()` is a **context provider**. At synthesis time, CDK calls the SSM API to fetch the parameter value, then caches the result in `cdk.context.json`. Subsequent `cdk synth` runs use the cached value unless you delete the cache entry or run with `cdk synth --no-lookups`. This makes synthesis repeatable without live AWS calls on every run.

Context providers exist for SSM, Secrets Manager, VPC lookups, DNS zone lookups, and availability zones.

### `CfnParameter` (CloudFormation Parameters)

`CfnParameter` maps to a CloudFormation `Parameters` section. The value is **supplied at deploy time**, not synthesis time. Use this for values that change between deployments without re-synthesizing — for example, an `EnvType` that selects different configuration inside the same template.

The tradeoff: `CfnParameter` values are opaque to CDK. You cannot use them to conditionally create resources or select different constructs, because CDK must decide those things during synthesis. For conditional logic, use context. For runtime configuration, use `CfnParameter`.

| Mechanism | Resolved at | Use case |
|-----------|-------------|----------|
| `try_get_context` / `require_get_context` | `cdk synth` | Resource selection, construct configuration |
| Context provider (SSM lookup) | `cdk synth` (first run) | Fetching dynamic AWS values at synthesis time |
| `CfnParameter` | `cdk deploy` / CloudFormation | Values that change per deployment without re-synth |

See [[environment-context]] for incorporating account/region into configuration, and [[hello-cdk]] for the app scaffold.
