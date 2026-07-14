---
tags:
  - security
  - iam
---

# IAM Roles, Managed Policies, and the CDK Grant Pattern

Creating IAM roles with trust policies, attaching managed and inline policies, and using the idiomatic `grant_*` methods that CDK resources expose.

## Code

```python
from aws_cdk import aws_iam as iam

# Role with a managed policy and an additional inline statement
role = iam.Role(self, "AppRole",
    assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "AmazonSSMManagedInstanceCore"
        )
    ],
)
role.add_to_policy(iam.PolicyStatement(
    actions=["s3:ListBucket"],
    resources=[bucket.bucket_arn],
))

# Grant pattern — the idiomatic CDK permission model
bucket.grant_read(role)                     # adds s3:GetObject* to role
queue.grant_send_messages(fn)               # adds sqs:SendMessage to fn's role
table.grant_read_write_data(role)            # adds dynamodb:BatchGetItem, etc.

# Custom action set via .grant()
key.grant(role, "kms:Decrypt", "kms:Encrypt")

# Composite principal for multiple trust sources
iam.Role(self, "HybridRole",
    assumed_by=iam.CompositePrincipal(
        iam.ServicePrincipal("ec2.amazonaws.com"),
        iam.AccountPrincipal("123456789012"),
    ),
)

# Import an existing managed policy by ARN
iam.ManagedPolicy.from_managed_policy_arn(
    self, "ImportedPolicy",
    managed_policy_arn="arn:aws:iam::123456789012:policy/MyCustomPolicy",
)
```

## What's Happening

- **`grant_*` methods** are the idiomatic CDK way to add permissions. Each L2 resource that supports IAM (S3 buckets, SQS queues, DynamoDB tables, KMS keys, Lambda functions, etc.) exposes `grant_read(principal)`, `grant_write(principal)`, `grant_read_write(principal)`, and often resource-specific variants (e.g., `grant_send_messages`, `grant_put_object`). These methods compose the correct ARN, actions, and conditions for that resource type, reducing the chance of policy mistakes.

- **`grant(principal, *actions)`** is the generic variant — it adds the specified actions scoped to the resource's ARN. The method is safe to call multiple times: CDK deduplicates actions per statement so repeated calls do not produce duplicate IAM entries.

- **`assumed_by`** sets the trust policy (`AssumeRolePolicyDocument`) on the role. The principal type determines which IAM trust policy key CDK uses:
  - `ServicePrincipal` — `"Service": ["ec2.amazonaws.com"]`
  - `AccountPrincipal` — `"AWS": ["123456789012"]`
  - `FederatedPrincipal` — `"Federated": [arn]` (SAML, OIDC, Cognito)
  - `ArnPrincipal` — `"AWS": [arn]` (single IAM user/role)
  - `CompositePrincipal` — merges multiple principals into one statement

- **`managed_policies`** attaches AWS-managed or customer-managed policies to the role. `from_aws_managed_policy_name()` takes the short name (e.g., `"AmazonSSMManagedInstanceCore"`) and resolves the ARN during synthesis. `from_managed_policy_arn()` takes an explicit ARN for customer-managed policies. Managed policies are separate CloudFormation resources from the role — they are attached via `AWS::IAM::Role.Policies` (inline) or `AWS::IAM::Policy` (managed).

- **`add_to_policy()`** appends a `PolicyStatement` to the role's inline policy. Multiple calls accumulate into a single inline policy on the role. Unlike managed policies, inline policies are deleted when the role is deleted, which can be desirable for tightly scoped permissions. Inline policies count toward the 10 KB size limit per entity.

### Key CDK Concepts

- **`grant_*` is not a validation step** — it generates CloudFormation IAM policy JSON at synth time. There is no call to AWS IAM to verify the actions or resource ARNs exist. A `grant_read` on a bucket that was never deployed succeeds synthesis but fails at deploy time if the bucket name is malformed.
- **Deduplication** across `grant_*` calls means you can safely call `bucket.grant_read(role)` from both a dashboard construct and a data-processing construct without generating duplicate statements.
- **Cross-stack grants**: when `role` is in one stack and `bucket` in another, `bucket.grant_read(role)` creates a cross-stack reference, and CDK automatically adds the export/import `Fn::ImportValue` in the CloudFormation template.
- **`grant_*` methods return `iam.Grant`** objects with a `.success` / `.assert_success()` method if you need to test that a grant was applied in unit tests.

## Cross-Refs

See [[iam-policy-construction]] for manual `PolicyStatement` and `PolicyDocument` construction.
See [[lambda-hello-python]] for attaching a role to a Lambda function.
See [[ec2-basics]] for creating a role with SSM policy for EC2 instances.
See [[permission-boundaries]] for restricting grant effectiveness with a boundary policy.
