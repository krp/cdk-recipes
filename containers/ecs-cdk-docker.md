---
tags:
  - containers
  - compute
---

# ECS with Local Docker Build

Deploy an ECS Fargate task using a Docker image built from a local Dockerfile, with CDK managing the build, ECR push, and IAM permissions.

## Code

```python
from aws_cdk import Stack
from aws_cdk import aws_ecs as ecs

# ECS — image built from ./app/Dockerfile
task_def = ecs.FargateTaskDefinition(self, "TaskDef", cpu=256, memory_mib=512)
image = ecs.ContainerImage.from_asset("./app")
task_def.add_container("App",
    image=image,
    port_mappings=[ecs.PortMapping(container_port=80)],
)
```

And for Lambda container images:

```python
from aws_cdk import aws_lambda as lambda_

fn = lambda_.DockerImageFunction(self, "MyFn",
    code=lambda_.DockerImageCode.from_image_asset("./ml-handler"),
)
```

## What's Happening

- **`ContainerImage.from_asset("./app")** tells CDK to run `docker build -t cdkasset-<hash> ./app` during `cdk synth` or `cdk deploy`. CDK computes a hash of the Dockerfile and the entire build context directory — only when the hash changes does CDK rebuild and re-push. The hash is embedded in the CloudFormation template as a parameter, so stack updates also only trigger when the image content changes.

- CDK automatically creates an ECR repository (`AWS::ECR::Repository`) per asset, pushes the built image, and references the image URI by its digest. The repository name follows the pattern `cdk-hash-<asset-hash>-<region>`. CDK also attaches a lifecycle policy to expire untagged images (default: keep 3).

- **`DockerImageFunction`** wraps the same asset pattern for Lambda. Instead of configuring ECS, it creates a `AWS::Lambda::Function` with `PackageType: Image` and the ECR image URI. The Lambda execution role gets ECR pull access similarly to the ECS task role.

- **IAM permissions** are handled automatically: CDK grants the ECS task execution role (or Lambda execution role) permission to `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, and `ecr:BatchCheckLayerAvailability`. The repository resource policy also allows the service principal to pull. You do not need to add ECR grant calls manually.

- **Rebuild behavior**: CDK's asset system compares the source hash against the previously deployed hash. During `cdk deploy`, if the Docker context is unchanged, CDK skips the build and push entirely. If it has changed, CDK builds, pushes, and supplies the new image URI to CloudFormation, triggering an ECS service update or Lambda function version update.

### Key CDK Concepts

- The asset system (`aws-cdk-lib/aws-ecr-assets`) is the foundation: `ContainerImage.from_asset()` is syntactic sugar over `DockerImageAsset`. The asset construct produces a `BootstrapStack`-scoped S3 bucket and ECR repository per environment. Cross-account deployments require the bootstrap stack to be set up with `--trust`.

- `from_asset()` does **not** support Docker build arguments or multi-stage build targeting via the basic call. For advanced Docker options (build args, target stage, platform), use the lower-level `DockerImageAsset` construct:
  ```python
  from aws_cdk import aws_ecr_assets as ecr_assets

  asset = ecr_assets.DockerImageAsset(self, "MyImage",
      directory="./app",
      build_args={"BUILDKIT_INLINE_CACHE": "1"},
      target="production",
      platform=ecr_assets.Platform.LINUX_AMD64,
  )
  image = ecs.ContainerImage.from_docker_image_asset(asset)
  ```

- Docker must be installed and running on the machine performing `cdk deploy` or `cdk synth`. If Docker is unavailable, CDK falls back to a previously pushed image digest only when the asset hash matches — never for a new hash.

- Lambda's `DockerImageFunction` is an L2 construct that handles `DockerImageCode` input. The underlying CloudFormation resource is `AWS::Lambda::Function` with `Code.ImageUri`. There is no custom resource or intermediate S3 bucket — the image URI flows directly into the function definition.

## Cross-Refs

See [[ecs-fargate-service]] for the full ALB + Fargate service pattern.
See [[lambda-hello-python]] for Lambda with inline code vs. container images.
