---
tags: ci-cd
---

# CDK Pipeline — Self-Mutating CodePipeline for Deploying CDK Apps

A CDK Pipelines `CodePipeline` that creates a self-mutating CI/CD pipeline from a CodeCommit source, synthesizes the CDK app, and deploys application stages.

## Code

```python
from aws_cdk import (
    Stack,
    Stage,
    pipelines,
    aws_codecommit as codecommit,
)
from constructs import Construct


class MyPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        repo = codecommit.Repository.from_repository_arn(
            self, "Repo",
            repository_arn="arn:aws:codecommit:us-east-1:123456789012:MyApp",
        )

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.code_commit(repo, "main"),
                commands=[
                    "pip install -r requirements.txt",
                    "cdk synth",
                ],
            ),
        )

        pipeline.add_stage(
            ApplicationStage(self, "Prod", env={"account": "...", "region": "..."})
        )


class ApplicationStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        AppStack(self, "App")
```

## What's Happening

- **`CodePipeline`** is CDK's L2 construct for CI/CD. It creates an AWS CodePipeline, a CodeBuild project for the synth action, and the self-mutation stage. The pipeline infrastructure (the CodePipeline itself, the build project, the artifact bucket, and the IAM roles) is deployed from the stack that contains the `CodePipeline` construct.

- **Self-mutation:** After the Synth step, CDK generates a self-mutate step that compares the pipeline's current definition against the synthesized output. If the pipeline definition changed (e.g., a new stage was added), the self-mutate step updates the pipeline stack before deploying any application stages. This means the pipeline can safely change its own structure — the self-mutation runs first.

- **`ShellStep` vs `CodeBuildStep`:** `ShellStep` runs commands inline with minimal configuration (simpler to write and read). `CodeBuildStep` exposes the full CodeBuild project properties: custom build image, compute type, environment variables, and VPC configuration. Use `ShellStep` for standard `pip install` / `cdk synth` workflows; use `CodeBuildStep` when you need a specific build environment or network isolation.

- **`Stage`** is a CDK construct group (`aws_cdk.Stage`) that synthesizes into a separate CloudFormation stack within the pipeline. Each `Stage` can contain multiple stacks — they are deployed together as a single pipeline action. The `Stage` class creates a deployment boundary: stacks inside a stage are never mixed with stacks from other stages.

- **`add_stage()`** creates a deployment stage in the pipeline. CDK automatically adds pre/post hooks (manual approvals, integration tests) using:
  ```python
  pipeline.add_stage(
      ApplicationStage(...),
      pre=[pipelines.ManualApprovalStep("Promote")],
      post=[pipelines.ShellStep("SmokeTest", commands=["curl ..."])],
  )
  ```

- **Cross-account permissions:** If pipeline stages target different AWS accounts, CDK automatically synthesizes the cross-account IAM roles and generates the necessary stack outputs. The pipeline's synth stack retains a list of target accounts and regions.

- **`cdk synth` is the pipeline's core action:** The pipeline runs `cdk synth` to validate the app can synthesize and to produce the Cloud Assembly (the set of synthesized CloudFormation templates and assets). Without a successful synth, no pipeline action executes.

### Key CDK Concepts

- `pipelines.CodePipeline` is a high-level L2 construct that creates multiple CloudFormation resources: `AWS::CodePipeline::Pipeline`, `AWS::CodeBuild::Project`, `AWS::S3::Bucket` (artifact store), and `AWS::IAM::Role` (pipeline and build roles).
- Self-mutation is implemented as a CodeBuild project that runs `cdk deploy PipelineStack` using the pipeline's own Cloud Assembly. CDK Pipelines manages this — you do not write the self-mutation logic.
- `CodePipelineSource.code_commit()` is a factory method that returns an `IFileSetProducer`. During synthesis it configures the pipeline's source stage with the repository and branch.
- `ShellStep` commands run in a CodeBuild environment managed by CDK Pipelines. The commands receive the source artifact in the working directory.
- `Stage` is a construct from `aws_cdk` (not `constructs`). It has its own synthesis boundary — each stage produces exactly one CloudFormation stack per nested stack.
- The pipeline stack (the one defining `CodePipeline`) must be deployed manually (or via a bootstrap pipeline) — after the first deploy, the self-mutation mechanism takes over.

## Cross-Refs

See [[multiple-stacks]] for managing stacks within a stage.
See [[environment-context]] for configuring stage environment accounts and regions.
See [[testing-with-assertions]] for validating synthesized pipeline templates.
