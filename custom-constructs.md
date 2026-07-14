---
tags: advanced
---

# Custom Constructs

Writing a custom `Construct` class that encapsulates multiple CDK resources into a single reusable abstraction.

## Code

```python
from constructs import Construct
from aws_cdk import aws_s3 as s3, aws_iam as iam, RemovalPolicy, Duration

class SecureBucket(s3.Bucket):
    """S3 bucket with enforced encryption, logging, and lifecycle."""
    def __init__(self, scope: Construct, id: str, *,
                 encryption=s3.BucketEncryption.S3_MANAGED,
                 versioned=True,
                 **kwargs):
        super().__init__(scope, id,
                         encryption=encryption,
                         versioned=versioned,
                         **kwargs)
        # Deny any request that does not use TLS
        self.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:*"],
            resources=[self.arn_for_objects("*"), self.bucket_arn],
            conditions={"Bool": {"aws:SecureTransport": "false"}},
            effect=iam.Effect.DENY,
        ))
```

A bundle construct that composes multiple resources rather than extending one:

```python
import aws_cdk.aws_dynamodb as ddb
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_ec2 as ec2

class AppTier(Construct):
    def __init__(self, scope: Construct, id: str, *,
                 vpc: ec2.IVpc,
                 **kwargs):
        super().__init__(scope, id, **kwargs)

        self.table = ddb.Table(self, "Table",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
        )

        self.queue = sqs.Queue(self, "Queue",
            visibility_timeout=Duration.seconds(300),
        )

        self.fn = lambda_.Function(self, "Fn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            vpc=vpc,
        )
```

## What's Happening

- **Constructs are the unit of composition** in CDK. Every AWS resource, every stack, and every reusable pattern is a construct. A custom construct is any class that extends `Construct` or a resource L2 (Bucket, Table, Queue, etc.).
- **Props pattern**: Use keyword-only arguments (`*`, `**kwargs`) with type hints for simple constructs. For constructs with many parameters or that are part of a public library, define a `@dataclass` Props class — see [[construct-patterns]].
- **The `self` scope pattern**: Child resources are added to `self` (the construct itself) as their scope. This makes the construct the owner of those resources in the construct tree. CDK uses the construct tree for synthesis: every child becomes a CloudFormation resource, and the logical ID is derived from the construct path (`scope/id`).
- **Extending vs composing**: Extending (`SecureBucket(s3.Bucket)`) adds opinionated defaults to a single resource type — all Bucket methods are still inherited. Composing (`AppTier(Construct)`) bundles multiple resources into one abstraction. Compose unless you genuinely need to substitute the construct everywhere the parent class is accepted.
- **Construct IDs must be unique within their scope**: CDK uses the construct path (`<scope>/<id>`) to generate CloudFormation logical IDs. Two children with the same `id` under the same scope cause a synthesis error.
- **Expose attributes**: Assign child resources to `self.<name>` so consumers can grant permissions, access properties, or pass them to other constructs. Private attributes (`self._table`) hide implementation details behind a forwarding method — see `grant_process` in [[construct-patterns]].

### Key CDK Concepts

- Every construct implements the `constructs.Construct` base, which provides the scope/ID pattern, the construct tree, and `node` attributes
- The `**kwargs` pattern lets consumers pass inherited resource props (e.g., `bucket_name`, `removal_policy`) without the custom construct having to enumerate them
- `super().__init__()` must be called before creating child resources — the scope parent must be established first

## Cross-Refs

See [[construct-patterns]] for reusable grant forwarding and interface props.
See [[hello-cdk]] for the minimal app scaffold.
See [[escape-hatches]] for accessing the underlying L1 resource from a custom construct.
