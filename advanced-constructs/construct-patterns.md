---
tags:
  - advanced
---

# Construct Patterns

Reusable patterns for custom constructs: grant method forwarding, interface-based props, and composition.

## Code

```python
from constructs import Construct
from aws_cdk import aws_iam as iam

class AppTier(Construct):
    def __init__(self, scope: Construct, id: str, *,
                 table: ddb.Table,
                 queue: sqs.Queue,
                 processing_fn: lambda_.Function):
        super().__init__(scope, id)
        self._table = table
        self._queue = queue
        self._fn = processing_fn

    def grant_process(self, grantee: iam.IGrantable) -> None:
        self._table.grant_read_write(grantee)
        self._queue.grant_consume_messages(grantee)
        self._queue.grant_send_messages(grantee)
```

Defining props with a dataclass for complex constructs:

```python
from dataclasses import dataclass
from aws_cdk import aws_ec2 as ec2

@dataclass
class TierProps:
    """Properties for AppTier construct."""
    vpc: ec2.IVpc
    stage: str
    enable_monitoring: bool = True
    removal_policy: RemovalPolicy = RemovalPolicy.RETAIN

class AppTier(Construct):
    def __init__(self, scope: Construct, id: str, *,
                 props: TierProps):
        super().__init__(scope, id)
        # Use props.vpc, props.stage, etc.
```

Importing an existing resource into a construct:

```python
class AppTier(Construct):
    @staticmethod
    def from_existing(scope: Construct, id: str, *,
                      table: ddb.ITable) -> "AppTier":
        return AppTier(scope, id, table=table)

    def __init__(self, scope: Construct, id: str, *,
                 table: ddb.ITable = None,
                 **kwargs):
        super().__init__(scope, id, **kwargs)
        self._table = table or ddb.Table(self, "Table", ...)
```

## What's Happening

- **`grant_*` forwarding**: Your construct exposes the same grant API as the inner resources so consumers call `tier.grant_process(role)` instead of reaching through private attributes (`tier._queue.grant_send(role)`). This preserves encapsulation and lets you change internals without breaking callers.
- **`iam.IGrantable` protocol**: Any construct that has a `grantPrincipal` property — `iam.Role`, `iam.User`, `iam.Group`, `iam.ServicePrincipal`, Lambda function roles, etc. — implements this interface. Writing `grantee: iam.IGrantable` means your method accepts all of them.
- **Props via `@dataclass`**: Gives you type-checked attribute access and default values. Use this pattern when a construct has more than 2–3 configuration parameters or when the same props are reused across multiple constructs.
- **Interface segregation**: Accept `ec2.IVpc` (the interface) not `ec2.Vpc` (the concrete class). This lets callers pass imported VPCs (`ec2.Vpc.from_lookup()`) or mock VPCs in tests.
- **`from_existing_*` static methods**: The standard CDK pattern for importing an existing resource into a construct without creating a new one. The method returns a construct instance that wraps the imported resource. CDK service modules follow this pattern: `s3.Bucket.from_bucket_name()`, `ec2.Vpc.from_lookup()`, etc.
- **Forwarding other methods**: Beyond grants, you may want to forward `metric_*` (CloudWatch metrics), `connections` (security groups), or `env` (resource environment). Choose what is useful for consumers and forward only those — do not create a pass-through proxy of every inner method.

### Key CDK Concepts

- A construct that only forwards `grant_*` does not generate CloudFormation resources itself — it is a grouping construct. The CloudFormation template contains only the resources it composes.
- `IGrantable` vs `IPrincipal`: `IGrantable` is anything with a `grantPrincipal` (roles, users, Lambda functions). `IPrincipal` is a policy principal used in `PolicyStatement`. Most `grant_*` methods on L2 resources accept `IGrantable`.

## Cross-Refs

See [[custom-constructs]] for the basics of writing custom constructs.
See [[iam-roles-and-grants]] for the full grant pattern and IAM principal types.
