---
tags: security, storage
---

# KMS Key with Grants, Alias, Rotation, Multi-Region Replica, and Cross-Account Access

Creating a symmetric KMS CMK with automatic rotation, an alias, grants to principals, integration with S3 bucket encryption, cross-account resource policies, and multi-region key support.

## Code

```python
from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam

# Symmetric CMK with rotation and alias
key = kms.Key(self, "AppKey",
    alias="app-key",
    enable_key_rotation=True,
    pending_window=Duration.days(7),
    removal_policy=RemovalPolicy.DESTROY,
)

# Grant actions to a principal
key.grant_encrypt(lambda_fn)   # adds kms:Encrypt to fn's role
key.grant_decrypt(lambda_fn)   # adds kms:Decrypt

# Use the key for S3 SSE-KMS
bucket = s3.Bucket(self, "SecureBucket",
    encryption_key=key,
    encryption=s3.BucketEncryption.KMS,
)

# Cross-account access — add a resource policy statement
key.add_to_resource_policy(iam.PolicyStatement(
    actions=["kms:Decrypt"],
    resources=["*"],
    principals=[iam.AccountPrincipal("999999999999")],
))

# Multi-Region key (replicas follow the primary)
multi_region_key = kms.MultiRegionKey(self, "GlobalKey",
    alias="global-app-key",
    enable_key_rotation=True,
)

# Replica in another region
kms.MultiRegionKey(self, "GlobalKeyReplica",
    alias="global-app-key",
    region="eu-west-1",
    primary_key=multi_region_key,
)
```

## What's Happening

- **`kms.Key`** is the L2 construct for a symmetric encryption KMS key (the default `key_spec` is `SYMMETRIC_DEFAULT`). Symmetric keys are used for both encryption and decryption and are the primary choice for most AWS integrations (S3, EBS, RDS, Lambda env vars). Asymmetric keys (`key_spec=ECC_NIST_P256` or `RSA_2048`) are available via `kms.Key` for sign/verify or encrypt/decrypt use cases that need separate public/private key pairs.

- **`enable_key_rotation=True`** sets `RotationPeriodInDays` to 365 (the maximum allowed for customer-managed keys). AWS KMS rotates the key material annually while retaining the old backing key so data encrypted before rotation remains decryptable. Key rotation does not invalidate grants, aliases, or resource policies — the key ID and ARN remain stable.

- **`grant_encrypt` / `grant_decrypt`** add the correct KMS actions (`kms:Encrypt` / `kms:Decrypt`) and the key's resource ARN to the principal's IAM role. The grants are scoped to this specific key — the principal cannot use other KMS keys. These methods are safe to call multiple times; CDK deduplicates the resulting IAM statement.

- **`BucketEncryption.KMS` + `encryption_key`** configures the bucket to use SSE-KMS with the specified key. CDK sets the bucket's `BucketEncryption` property to use the key ARN and adds the necessary `kms:GenerateDataKey` permission to the bucket's service role automatically. Without `encryption_key`, `BucketEncryption.KMS` uses the AWS-managed KMS key for S3 (which has a different key ARN and no rotation control).

- **Cross-account KMS** requires an explicit resource policy on the key granting access to the foreign account principal. `key.add_to_resource_policy()` appends a statement to the key's `AWS::KMS::Key.KeyPolicy`. The grant alone is insufficient — IAM in the target account must also allow the action, and the key policy must trust the foreign account. The resource ARN in the policy statement is always `"*"` for KMS key policies (KMS ignores the `Resource` field in key policies and uses the key ARN instead).

- **Multi-Region keys** (`kms.MultiRegionKey`) create a primary key in one region and replicas in others. All replicas share the same key material and key ID, so data encrypted in one region can be decrypted in another without cross-region KMS calls. The primary key controls rotation and deletion — replica keys cannot be rotated independently. `MultiRegionKey` is a separate construct from `kms.Key` because the underlying CloudFormation resource (`AWS::KMS::ReplicaKey`) differs.

### Key CDK Concepts

- **`pending_window`**: the number of days between key deletion and actual deletion (7–30 days, default 30). During this window, the key enters the `PendingDeletion` state and cannot be used. Canceling deletion within the window restores the key.
- **`RemovalPolicy.DESTROY`** maps to `DeletionPolicy: Delete` on the CloudFormation key resource. Without this, the default `RemovalPolicy.RETAIN` leaves the key in the account after stack deletion — safe but creates orphaned keys. For non-production stacks, `DESTROY` with a short `pending_window` avoids accumulation of unused keys.
- **KMS key ARN** is a CDK token (`{ "Fn::GetAtt": ["AppKey", "Arn"] }`), resolved at deploy time. Passing `key.key_arn` to another construct creates a CloudFormation reference between the resources.

## Cross-Refs

See [[s3-bucket-props]] for bucket encryption options and `BucketEncryption` enum variants.
See [[secrets-manager]] for KMS-backed secret encryption.
See [[iam-roles-and-grants]] for how `grant_encrypt` / `grant_decrypt` compose IAM statements.
See [[permission-boundaries]] for restricting cross-account KMS grants.
