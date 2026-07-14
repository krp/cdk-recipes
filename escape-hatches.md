---
tags:
  - advanced
---

# Escape Hatches

Accessing L1 (Cfn*) resources when the L2 construct does not expose a needed feature, and applying raw JSON property overrides.

## Code

```python
from aws_cdk import aws_s3 as s3

bucket = s3.Bucket(self, "Bucket")

# Access the underlying CloudFormation resource (L1)
cfn_bucket = bucket.node.default_child  # type: aws_s3.CfnBucket

# Set properties the L2 does not expose
cfn_bucket.object_lock_enabled = True

# Override any CloudFormation property — CDK does not validate the shape
cfn_bucket.add_property_override("ObjectLockConfiguration", {
    "ObjectLockEnabled": "Enabled",
    "Rule": {
        "DefaultRetention": {
            "Mode": "GOVERNANCE",
            "Days": 30,
        },
    },
})

# Metadata, deletion policy, and other CloudFormation options
cfn_bucket.cfn_options.metadata = {"Key": "Value"}
cfn_bucket.cfn_options.deletion_policy = aws_cdk.CfnDeletionPolicy.RETAIN
cfn_bucket.cfn_options.update_policy = aws_cdk.CfnUpdatePolicy(
    auto_scaling_rolling_update=aws_cdk.CfnAutoScalingRollingUpdate(
        pause_time=Duration.minutes(5),
    ),
)
```

Creating a raw CloudFormation resource with `CfnResource`:

```python
from aws_cdk import CfnResource

cfn = CfnResource(self, "RawResource",
    type="Custom::Something",
    properties={"Key": "Value"},
)
```

Removing a property that the L2 set:

```python
cfn_bucket.add_property_deletion_override("BucketEncryption.ServerSideEncryptionConfiguration")
```

## What's Happening

- **Every L2 has a `.node.default_child`** that is the underlying L1 (Cfn*) CloudFormation resource. For single-resource L2s (Bucket, Table, Queue, etc.), `default_child` returns the corresponding `CfnBucket`, `CfnTable`, `CfnQueue`. For composite L2s that create multiple resources, `default_child` returns the primary resource or `None` — you may need to find the right child via `node.children`.
- **`add_property_override()`** sets any CloudFormation property on the resource, even if the L2 does not model it. The argument is a raw JSON object that CDK merges into the synthesized template property section. Use this when the L2 omits a newer CloudFormation feature.
- **`add_property_deletion_override()`** removes a property that the L2 set, which is useful when you want to revert a default the L2 applies.
- **`cfn_options`** gives you direct access to CloudFormation-level settings: `creation_policy`, `update_policy`, `deletion_policy`, `metadata`, `update_replace_policy`. These are separate from the resource properties and control how CloudFormation handles the resource during stack operations.
- **`CfnResource(type, properties)`** is the rawest escape hatch — you specify the CloudFormation resource type and properties as a dict. CDK synthesizes this verbatim into the template. Use this for custom resource types, CloudFormation registry extensions, or resource types CDK has not released an L2 for yet.
- **When to use escape hatches**: The L2 does not expose a feature (new CloudFormation property, unsupported resource type), or you are migrating an existing CloudFormation template and want to keep the original property structure.
- **Caveat**: CDK does not validate overrides. An incorrect property name or value surfaces only at deploy time when CloudFormation rejects the template. Unit test your synthesized template or use `cdk synth --no-staging` to inspect the output before deploying.

### Key CDK Concepts

- The L1 construct classes (`CfnBucket`, `CfnTable`, etc.) are auto-generated from the CloudFormation resource schema. Every CloudFormation property has a corresponding Python property on the Cfn class.
- L2 constructs are opinionated wrappers around L1s. When the opinion does not match your requirement, drop to the L1 via `default_child` rather than replacing the L2 with a raw `CfnResource`.
- Overrides are applied at synthesis time. CDK serializes the construct tree to JSON, merges overrides into the resource properties, then produces the final template.
- Multiple overrides on the same property merge — the last override wins for conflicting keys. Use `add_property_deletion_override` to clear a key before setting it.

## Cross-Refs

See [[custom-resources]] for implementing `Custom::*` resources with Lambda-backed providers.
See [[custom-constructs]] for wrapping escape hatch logic inside a reusable construct so callers get the L2 API with the override baked in.
