---
tags:
  - storage
---

# S3 Bucket with Encryption, Versioning, Lifecycle, and Intelligent-Tiering

A production-grade S3 bucket configured with server-side encryption, versioning, lifecycle rules for tier transitions and expiration, and intelligent-tiering archive policy.

## Code

```python
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    Duration,
)
from constructs import Construct


class DataLakeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(
            self,
            "DataLake",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="StandardToInfrequentAccess",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                            transition_after=Duration.days(90),
                        ),
                    ],
                    expiration=Duration.days(365),
                ),
                s3.LifecycleRule(
                    id="ExpireNoncurrentVersions",
                    noncurrent_version_expiration=Duration.days(90),
                    noncurrent_version_transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(7),
                        ),
                    ],
                ),
            ],
            intelligent_tiering_configurations=[
                s3.IntelligentTieringConfiguration(
                    name="AllObjects",
                    archive_access_tier_time=Duration.days(90),
                    deep_archive_access_tier_time=Duration.days(180),
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
```

## What's Happening

- **`BucketEncryption.S3_MANAGED`** uses SSE-S3 (AES-256), where AWS manages the keys transparently. Use this when you don't need customer-controlled keys or audit trails. Use `BucketEncryption.KMS` (SSE-KMS) when you need key rotation control, cross-account access, or CloudTrail key usage logs — but remember KMS API rate limits (5,500/10,000 per second per region) apply to every `GetObject`/`PutObject` call using a KMS key.

- **Lifecycle rules** synthesize to CloudFormation `AWS::S3::Bucket.LifecycleConfiguration` — CDK transforms each `LifecycleRule` into the CFN property structure, but the rule ID must be unique per bucket or CloudFormation will reject the update. Transitions move objects between storage classes on the specified day count from object creation; expiration permanently deletes them.

- **`auto_delete_objects=True`** generates a custom resource (an AWS Lambda behind the scenes) that empties the bucket before CloudFormation deletes it. Without this, `RemovalPolicy.DESTROY` on a non-empty bucket causes a stack deletion failure because CloudFormation cannot delete a bucket that still contains objects.

- **`BlockPublicAccess`** defaults to `BlockPublicAccess.BLOCK_ALL` — CDK blocks all public access by default, overriding the less-restrictive AWS console default. This means `public_read_access=True` is silently ignored unless you also set `block_public_access` to a permissive value.

- **`RemovalPolicy.DESTROY`** maps to CloudFormation `DeletionPolicy: Delete`. The alternative `RemovalPolicy.RETAIN` maps to `DeletionPolicy: Retain`, leaving the bucket and all objects in your AWS account after stack deletion — a safety net that also requires manual cleanup.

### Key CDK Concepts

- `Duration` objects (not raw seconds) — CDK resolves them to seconds during synthesis, but the type keeps intent explicit.
- `IntelligentTieringConfiguration` is a separate construct property, not part of a lifecycle rule — tiering auto-migrates objects between access tiers based on usage patterns, while lifecycle rules are time-based transitions.
- The `Bucket` L2 construct synthesizes to a single `AWS::S3::Bucket` resource, plus a custom resource Lambda when `auto_delete_objects=True`.

## Cross-Refs

See [[your-first-bucket]] for the minimal bucket setup.
See [[kms-key-management]] for KMS key creation and rotation patterns.
See [[custom-resources]] for how `auto_delete_objects` works under the hood.
