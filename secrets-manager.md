---
tags: security
---

# Secrets Manager Secret with Rotation, Dynamic References, and Lambda Integration

Creating a Secrets Manager secret with a rotation schedule (hosted rotation), granting read access to a Lambda function, and using dynamic references that resolve at deploy time.

## Code

```python
from aws_cdk import RemovalPolicy, CfnOutput
from aws_cdk import aws_secretsmanager as secrets
import json

# Secret with inline secret string and hosted rotation
secret = secrets.Secret(self, "DbSecret",
    secret_string=json.dumps({"username": "admin", "password": "change-me"}),
    removal_policy=RemovalPolicy.DESTROY,
    rotation=secrets.RotationSchedule(
        hosted_rotation=secrets.HostedRotation.mysql_single_user(),
    ),
)

# Output the ARN for passing to other services
CfnOutput(self, "SecretArn", value=secret.secret_arn)

# Grant read access to a Lambda function
secret.grant_read(lambda_fn)

# Reference an existing secret (no rotation schedule)
existing = secrets.Secret.from_secret_complete_arn(
    self, "ImportedSecret",
    secret_complete_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-abc123",
)
```

## What's Happening

- **`Secret`** is the L2 construct for AWS Secrets Manager. It creates the `AWS::SecretsManager::Secret` CloudFormation resource, and optionally a `AWS::SecretsManager::RotationSchedule` and the rotation Lambda when `rotation` is specified. The secret name is auto-generated from the construct path unless you provide `secret_name`.

- **`secret_string` / `secret_string_binary`** accept a string value that CDK embeds directly in the CloudFormation template as plaintext. This means the secret value is visible in the CloudFormation template, the synthesized JSON, and the AWS CloudFormation console — only use it for development or test stacks. For production, create the secret with a generated password or reference an existing secret via `from_secret_complete_arn()`.

- **`HostedRotation.mysql_single_user()`** is a CDK L2 helper that creates a Lambda function from an AWS-managed rotation template for the specified database engine. CDK bundles the rotation code, creates the Lambda execution role with the necessary permissions, and configures the `RotationSchedule` resource. Supported engines: `mysql_single_user`, `mysql_multi_user`, `postgres_single_user`, `postgres_multi_user`, `oracle_single_user`, `mariadb_single_user`, `sqlserver_single_user`, `redshift_single_user`, `mongodb_single_user`. Multi-user variants create two secrets (one for the master, one for the application user) and rotate them on different schedules.

- **`secret.secret_arn`** is a CDK token that resolves to the `Ref` of the secret in CloudFormation. The IAM action `secretsmanager:GetSecretValue` is performed at deploy time (by the rotation Lambda) or at runtime (by the consuming service). The CloudFormation template contains a reference, not the secret value itself.

- **`grant_read()`** adds `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` to the principal's IAM role, scoped to this secret's ARN. This is sufficient for a Lambda function to retrieve the secret value via the SDK at runtime. There is no `grant_write()` on the L2 — write access (`secretsmanager:PutSecretValue`) is implicitly granted to the rotation Lambda.

- **`from_secret_complete_arn()`** imports an existing secret into the stack without managing its lifecycle. The imported object exposes `secret_arn`, `secret_name`, and `secret_value` (for dynamic references) but cannot add rotation or removal policies. Use this to reference secrets created outside the CDK app or in another stack.

### Key CDK Concepts

- **Dynamic references vs CDK tokens**: `secret.secret_arn` is a CDK token that resolves during CloudFormation deployment. The secret value itself is never in the CDK synthesis output — it is retrieved at deploy time (for `RotationSchedule`) or at runtime (for Lambda application code). CDK also provides `secret.secret_value` which returns a `SecretValue` object (a CloudFormation dynamic reference `{{resolve:secretsmanager:...}}`) for use in container environment variables, RDS master password properties, and similar constructs that support dynamic references.
- **Rotation Lambda permissions**: CDK automatically creates a Lambda execution role with `secretsmanager:GetSecretValue`, `secretsmanager:PutSecretValue`, `secretsmanager:UpdateSecretVersionStage`, and KMS decrypt permissions. The Lambda resource is managed by CDK and appears in the stack as a custom resource.
- **Removal policy**: `RemovalPolicy.DESTROY` causes CloudFormation to delete the secret on stack deletion. Without it, the default `RETAIN` keeps the secret in the account (with its `DeletionPolicy: Retain`), preventing accidental data loss but requiring manual cleanup.

## Cross-Refs

See [[kms-key-management]] for KMS key configuration — Secrets Manager uses a KMS key (default or customer-managed) to encrypt secret values.
See [[iam-roles-and-grants]] for the grant pattern that powers `secret.grant_read()`.
See [[ecs-fargate-service]] for using secrets in container environment variables via `ecs.Secret.from_secrets_manager()`.
See [[rds-instance]] for automatic master password via `rds.DatabaseSecret`.
