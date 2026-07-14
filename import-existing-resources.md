---
tags: migration, advanced
---

# Import Existing Resources

Reference existing AWS resources in your CDK app without CDK managing them directly.

## Code

```python
# Import existing bucket by name — no CloudFormation resource generated
bucket = s3.Bucket.from_bucket_name(self, "ImportedBucket", "my-existing-bucket")

# Import existing VPC by ID
vpc = ec2.Vpc.from_lookup(self, "ImportedVpc", vpc_id="vpc-12345")

# Import existing security group
sg = ec2.SecurityGroup.from_security_group_id(self, "ImportedSG", "sg-12345")
```

## What's Happening

- `from_*` static methods create a CDK reference to an existing resource — no CloudFormation resource is generated in the template
- These return interface types (`IBucket`, `IVpc`, `ISecurityGroup`), not concrete L2 construct instances
- CDK cannot modify resources imported via `from_*` — they can only be referenced as properties of other resources (e.g., passing a bucket ARN to a Lambda function)
- `from_lookup()` vs `from_*_attributes()` vs `from_*_arn()`: lookup queries the account at synthesis time via context providers (requires the resource to exist); attributes build the reference from known ARN components without runtime queries; arn methods parse the ARN string directly
- Resource import (`cdk import`) brings existing CloudFormation-managed resources into CDK by generating a template that matches their current logical IDs and physical resources — distinct from `from_*` references
- `from_lookup()` results are cached in `cdk.context.json` — invalidate by deleting the cache entry or running `cdk context --reset`

### Key CDK Concepts

- Interface types (`IBucket` et al.) are the return type of every `from_*` method — they expose only the subset of properties CDK resolved from the existing resource (ARN, name, etc.)
- Lookup-based imports depend on context provider SDK calls — they fail at synth time if the resource doesn't exist in the target account
- Escape hatch: if the interface doesn't expose a property you need, cast down to `CfnResource` and read raw attributes

Cross-ref: [[escape-hatches]], [[environment-context]], [[permission-boundaries]]
