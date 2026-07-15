---
tags:
  - foundation
  - storage
---

# Your First Bucket

Deploy an S3 bucket with CDK.

## Code

```python
from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_s3 as s3

class BucketStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        bucket = s3.Bucket(self, "MyFirstBucket")

# After synth, inspect the generated template:
# stack = BucketStack(app, "BucketStack")
# print(stack.to_json())
```

## What's Happening

`s3.Bucket(self, "MyFirstBucket")` instantiates an **L2 construct**. CDK offers three layers of constructs:

| Layer | Example | What it does |
|-------|---------|--------------|
| L1 (low-level) | `CfnBucket` | 1:1 mapping to a CloudFormation resource — every property matches the CFN spec. |
| L2 (curated) | `Bucket` | Opinionated defaults, convenience methods (`.grant_read()`, `.add_lifecycle_rule()`), and auto-generated physical names. |
| L3 (patterns) | `CloudFrontWebDistribution` | Multi-resource architectures built from L2s. |

The L2 `Bucket` sets sensible defaults: encryption (S3-managed), versioning disabled, public access blocked. It also generates a unique physical name — you don't provide one, so CDK lets CloudFormation auto-name it, avoiding name collisions across deploys.

### Logical ID Generation

Every construct gets a **logical ID** like `MyFirstBucketB8884501`. CDK derives it from the construct path (`BucketStack/MyFirstBucket`) and a hash of its parent structure. This logical ID is stable across deploys — CloudFormation uses it to track the resource across updates. If you rename the construct inside the stack, the logical ID changes and CloudFormation treats it as a resource replacement.

### Removal Policy

The default removal policy on an L2 `Bucket` is `RemovalPolicy.RETAIN`. Deleting the stack leaves the bucket in your account (and incurs storage costs). To have CloudFormation delete the bucket with the stack:

```python
s3.Bucket(self, "MyFirstBucket", removal_policy=RemovalPolicy.DESTROY)
```

With `DESTROY`, if the bucket still contains objects, stack deletion fails unless you also set `auto_delete_objects=True`, which adds a custom resource to empty the bucket before teardown.

### Physical Names

Pass `bucket_name="my-explicit-bucket"` to fix the physical name. This is **fragile**: if you deploy a second stack in another account or region with the same name, it fails. CDK-generated names are globally unique by design. Prefer generated names unless you have a hard requirement like a known bucket name for a third-party integration.

See [[hello-cdk]] for the minimal app scaffold, and [[s3-bucket-props]] for the full set of bucket configuration options.
