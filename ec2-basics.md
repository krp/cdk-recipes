---
tags: compute, networking
---

# EC2 Instance with SSM Session Manager, VPC, and User Data

An EC2 instance deployed into a CDK-managed VPC with SSM Session Manager for access, IAM role, and user data for bootstrapping.

## Code

```python
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct


class Ec2Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        role = iam.Role(
            self,
            "SSMRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        instance = ec2.Instance(
            self,
            "AppServer",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            vpc=vpc,
            role=role,
            user_data=ec2.UserData.custom(
                "#!/bin/bash\nyum install -y nginx"
            ),
        )
```

## What's Happening

- **`ec2.Vpc(max_azs=2)`** creates a full VPC with public subnets, private subnets, NAT gateways (one per AZ), Internet Gateway, and route tables — CDK's `Vpc` L2 construct synthesizes to roughly a dozen CloudFormation resources. The `max_azs=2` limits deployment to two Availability Zones, reducing cost from the default three at the expense of redundancy.

- **`ec2.Instance`** is the L2 construct for EC2 instances. It handles the network interface (`AWS::EC2::NetworkInterface`), security group, root volume (`AWS::EC2::Volume` + attachment), and the instance itself (`AWS::EC2::Instance`). It also attaches the IAM instance profile derived from the `role` parameter.

- **`UserData.custom()`** accepts raw shell script content and serializes it into the CloudFormation `UserData` property as base64-encoded text. The script runs as root on first boot. Use `instance.user_data.add_commands("yum update -y")` to append lines programmatically instead of concatenating strings.

- **SSM Session Manager** avoids SSH key pairs entirely. The IAM role with `AmazonSSMManagedInstanceCore` policy allows the SSM agent (pre-installed on Amazon Linux 2023) to register with AWS Systems Manager. Connect via `aws ssm start-session --target <instance-id>` — no open inbound ports, no bastion host, no key pair management.

- **Security group defaults**: `ec2.Instance` creates a security group with no inbound rules and a default outbound rule allowing all traffic. You add ingress via `instance.connections.allow_from(peer, port)`. For example, to allow HTTP from anywhere:
  ```python
  instance.connections.allow_from(
      ec2.Peer.any_ipv4(),
      ec2.Port.tcp(80),
  )
  ```

- **`machine_image.latest_amazon_linux2023()`** resolves to the latest Amazon Linux 2023 AMI published by AWS. CDK stores the resolved AMI ID in the CloudFormation template as a parameter or hard-coded value depending on the engine — use `machine_image=ec2.MachineImage.generic_linux({"us-east-1": "ami-..."})` for a static AMI.

### Key CDK Concepts

- `Vpc` with no explicit subnet configuration creates CDK's "default" subnet layout (public, private with NAT, isolated). Use `subnet_configuration` to customize.
- `ec2.Instance` requires at minimum `vpc`, `instance_type`, and `machine_image`. The construct defaults to a `t3.nano`-equivalent; always specify an `instance_type` explicitly for clarity.
- The instance's `instance.user_data` is a CDK object, not a raw string — CDK serializes it lazily during synthesis.

## Cross-Refs

See [[vpc-default]] for tuning the Vpc construct (subnet types, NAT gateways).
See [[vpc-custom]] for defining subnets and route tables manually.
See [[iam-roles-and-grants]] for IAM role and policy patterns in CDK.
