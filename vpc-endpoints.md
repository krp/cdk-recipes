---
tags: networking
---

# VPC Endpoints

Gateway Endpoints and Interface Endpoints for accessing AWS services from inside a VPC without traversing the public internet.

## Code

```python
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2

# Gateway Endpoint — free, uses prefix lists in route tables
vpc.add_gateway_endpoint("S3Endpoint",
    service=ec2.GatewayVpcEndpointAwsService.S3,
)

# Interface Endpoint — hourly cost + data processing, uses PrivateLink ENI
vpc.add_interface_endpoint("EcrEndpoint",
    service=ec2.InterfaceVpcEndpointAwsService.ECR,
)
vpc.add_interface_endpoint("LogsEndpoint",
    service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
)
```

## What's Happening

- **Gateway Endpoints** (S3, DynamoDB) are free of charge. They work by adding entries to the VPC route tables: traffic destined for the service's prefix list is routed through the AWS network backbone instead of the internet. No change to DNS resolution — the same S3 endpoint URLs work, but traffic stays within AWS. Gateway endpoints are regional and cannot be cross-region.

- **Interface Endpoints** (everything else: ECR, CloudWatch Logs, STS, KMS, etc.) cost approximately $0.01/hour per endpoint plus $0.01/GB of data processed. They create a PrivateLink Elastic Network Interface (ENI) in your subnet with a private IP from that subnet's range. DNS resolution of the service's public endpoint can optionally resolve to this private IP.

- `add_interface_endpoint` auto-creates a security group allowing inbound on port 443 from the VPC CIDR. Customize with `security_groups=` and `open=False`:
  ```python
  vpc.add_interface_endpoint("EcrEndpoint",
      service=ec2.InterfaceVpcEndpointAwsService.ECR,
      open=False,
      security_groups=[my_sg],
  )
  ```

- **Private DNS** (`private_dns_enabled=True`, default) enables a Route 53 private hosted zone that makes the default service DNS name (e.g., `ecr.us-east-1.amazonaws.com`) resolve to the endpoint ENI's private IP. Disable it when you need to control DNS resolution yourself or when using a custom endpoint name.

- **Endpoint policies** are JSON documents controlling which actions principals can perform through the endpoint. Default is full access. Restrict with a policy document:
  ```python
  from aws_cdk import aws_iam as iam

  vpc.add_gateway_endpoint("S3Endpoint",
      service=ec2.GatewayVpcEndpointAwsService.S3,
      policy=iam.PolicyDocument(
          statements=[
              iam.PolicyStatement(
                  principals=[iam.AnyPrincipal()],
                  actions=["s3:GetObject"],
                  resources=["arn:aws:s3:::my-bucket/*"],
              ),
          ],
      ),
  )
  ```

### Key CDK Concepts

- `add_gateway_endpoint` returns a `GatewayVpcEndpoint` construct; `add_interface_endpoint` returns `InterfaceVpcEndpoint`. Both are L2 constructs that synthesize to `AWS::EC2::VPCEndpoint` (L1 `CfnVPCEndpoint`) — the CloudFormation resource type is the same; the difference is the `VpcEndpointType` property.

- Gateway endpoints are a property of the VPC — they modify route tables. Interface endpoints are subnet-scoped: they place an ENI and must know which subnets to use. By default CDK places interface endpoints in every private subnet; use `subnets=` to restrict.

- Security group defaults differ: `add_gateway_endpoint` does not create a security group (gateway endpoints don't use one). `add_interface_endpoint` creates one with an inbound HTTPS rule from the VPC CIDR.

## Cross-Refs

See [[vpc-custom]] for setting up the VPC that hosts these endpoints.
See [[vpc-default]] for the default VPC pattern.
