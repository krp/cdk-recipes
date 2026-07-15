---
tags:
  - ci-cd
  - advanced
---

# Multi-Account Deployments

Deploy CDK stacks to multiple AWS accounts and regions using environment targeting or CDK Pipelines.

## Code

```python
# Per-stack environment binding
env_prod = Environment(account="111111", region="us-east-1")
env_staging = Environment(account="222222", region="us-west-2")

AppStack(app, "App-Prod", env=env_prod)
AppStack(app, "App-Staging", env=env_staging)

# With CDK Pipeline — stages deploy to separate accounts
pipeline.add_stage(ApplicationStage(self, "Staging", env=env_staging))
pipeline.add_stage(ApplicationStage(self, "Prod", env=env_prod))
```

## What's Happening

- Each stack with an explicit `env` synthesizes into a separate CloudFormation template targeted at that account and region — stacks without `env` are environment-agnostic and synthesize to a single template
- CDK Pipeline (`CodePipeline`) handles cross-account deployments through IAM roles created during bootstrap: a deployment role in the pipeline account assumes an execution role in each target account
- Prerequisites: every target account/region combination must be bootstrapped (`cdk bootstrap aws://ACCOUNT/REGION`) — the bootstrap stack creates the required S3 bucket, ECR repository, and IAM roles
- The pipeline uses a cross-account key (`cross_account_keys`) for the artifact bucket when deploying across accounts, enabled by default for cross-environment pipelines
- Stack sets (`CfnStackSet`) deploy the same template to multiple accounts/regions simultaneously — this is a CloudFormation feature, different from CDK Pipelines which orchestrates sequential deployments
- `from_lookup()` context providers do not work cross-account at synth time — the lookup is performed in the bootstrapped account's context, not the target account. Pass values explicitly or use SSM Parameter Store to share them across accounts

### Key CDK Concepts

- `Environment(account, region)` — it is a best practice to use concrete environment values; environment-agnostic stacks use token resolution that delays account/region binding until deployment
- When `env` specifies both account and region, CDK can resolve assets and context at synthesis time; omitting account/region produces a deploy-anywhere template that may require `--profile` at deploy time
- Pipeline stages deploy in sequence; waves run stages in parallel within a single pipeline

Cross-ref: [[environment-context]], [[cicd-pipeline]], [[stack-parameters-and-context]]
