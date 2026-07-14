---
tags: containers, compute
---

# ECS Fargate Service with ALB

An ECS Fargate service running a containerized application behind an Application Load Balancer, with task-level CPU and memory defined at deployment time — no EC2 instances to manage.

## Code

```python
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2

# Cluster — named compute capacity group within a VPC
cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

# Task definition — CPU and memory at the task level for Fargate
task_def = ecs.FargateTaskDefinition(self, "TaskDef",
    cpu=256,
    memory_mib=512,
)
task_def.add_container("App",
    image=ecs.ContainerImage.from_registry("nginx:alpine"),
    port_mappings=[ecs.PortMapping(container_port=80)],
)

# Service — runs the task definition
service = ecs.FargateService(self, "Service",
    cluster=cluster,
    task_definition=task_def,
)

# ALB — internet-facing, routes to the service
alb = elbv2.ApplicationLoadBalancer(self, "ALB",
    vpc=vpc,
    internet_facing=True,
)
listener = alb.add_listener("Listener", port=80)
listener.add_targets("Targets",
    port=80,
    targets=[service],
)
```

## What's Happening

- **`FargateTaskDefinition`** sets `cpu` and `memory_mib` at the task level, not per-container. Fargate allocates the requested resources as a unit and bills by vCPU-second and GB-second. Valid CPU/memory combinations are constrained by AWS Fargate limits — 256 CPU (0.25 vCPU) pairs with 512 MB, 1 GB, or 2 GB; 512 CPU pairs with 1 GB through 4 GB; and so on. An invalid combination causes a CloudFormation deployment failure, not a synth error.

- **`ContainerImage.from_registry("nginx:alpine")** pulls the image from Docker Hub at deployment time. Alternatives:
  - `from_ecr_repository(repo, tag)` — uses an existing ECR repository construct.
  - `from_asset("./app")` — builds from a local Dockerfile and pushes to a CDK-managed ECR repository (see [[ecs-cdk-docker]]).
  CDK does not validate the image exists during synth; failures surface at deploy time when ECS pulls the container.

- **`FargateService`** auto-creates a security group that allows inbound traffic from the ALB's security group (CDK handles this wiring when you pass the service as a target). The service also receives an IAM task execution role with the managed policy `AmazonECSTaskExecutionRolePolicy` for pulling images and writing logs.

- **`listener.add_targets(... targets=[service])`** registers the Fargate service as an ALB target group. CDK generates the target group, configures health checks against the container port, and wires the security group ingress from the ALB to the service. The target group health check defaults to HTTP `/` on the container port with a 30-second interval.

- **Auto-scaling** attaches an Application Auto Scaling target:
  ```python
    scaling = service.auto_scale_task_count(max_capacity=5)
    scaling.scale_on_cpu_utilization(
        "CpuScaling",
        target_utilization_percent=70,
    )
  ```
  This creates an `AWS::ApplicationAutoScaling::ScalableTarget` and a step scaling policy. The `target_utilization_percent` triggers scale-out when sustained CPU exceeds 70% and scale-in when it drops significantly below.

### Key CDK Concepts

- `ecs.Cluster(self, "Cluster", vpc=vpc)` with no additional props creates an empty cluster — it has no EC2 capacity, no capacity provider, and no ASG. Fargate services don't need any of those; the cluster is purely a logical grouping. For EC2-backed services you would add `cluster.add_capacity("Asg", ...)`.

- `FargateService`'s `task_definition` is an `ITaskDefinition` interface. CDK binds the service to the task definition during construct synthesis but the CloudFormation `AWS::ECS::Service` references the `AWS::ECS::TaskDefinition` via `Ref`.

- CDK generates the `AWS::ECS::Service` with `LaunchType: FARGATE`, `NetworkConfiguration` with the service's security group and the VPC subnets (default: private subnets). Override subnets with `vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)`.

## Cross-Refs

See [[ecs-cdk-docker]] for building and deploying a container from a local Dockerfile.
See [[vpc-custom]] for VPC setup with specific subnet tiers.
