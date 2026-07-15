---
tags:
  - networking
---

# Default VPC

The `Vpc` default construct creates a full multi-AZ VPC with public, private, and isolated subnets, plus NAT gateways and an Internet gateway — approximately 20 CloudFormation resources from one L2 constructor.

## Code

```python
from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2

# One line — ~20 CloudFormation resources
vpc = ec2.Vpc(self, "Vpc", max_azs=3)

# Inspect what was created
CfnOutput(self, "VpcId", value=vpc.vpc_id)
for subnet in vpc.public_subnets:
    CfnOutput(self, f"PubSubnet", value=subnet.subnet_id)
```

## What's Happening

- `ec2.Vpc` with no `ip_addresses` uses the default CIDR block (`10.0.0.0/16`). CDK synthesizes one `AWS::EC2::VPC`, then auto-generates subnets across three tiers (public, private, isolated), each stretched across the configured AZ count. It also adds an Internet gateway for the public tier, NAT gateways (one per AZ by default) for private-tier egress, and the corresponding route table entries.

- `max_azs=3` sets the AZ ceiling, but CDK looks up the account's available AZs in the region and uses the minimum of `max_azs` and the actual count. If a region exposes only 2 AZs, setting `max_azs=3` gives you 2. Use `availability_zones` (a literal list) if you need pinning to specific AZs.

- `vpc.vpc_id` and each `subnet.subnet_id` are **tokens** — CloudFormation `Ref` intrinsics (`{ "Ref": "VpcB9BD5F0B" }`). They aren't resolved until deploy time. Printing them at synth time yields `"${Token[TOKEN.117]}"`.

- `nat_gateways` defaults to one per AZ. Each NAT gateway costs approximately $0.045/hour + data processing fees ($0.045/GB). Set `nat_gateways=1` to share one gateway across all private subnets, though cross-AZ NAT traffic incurs an additional $0.01/GB data transfer charge.

- Subnets are exposed as `ISubnet` objects via the collections `vpc.public_subnets`, `vpc.private_subnets`, and `vpc.isolated_subnets`. Each `ISubnet` carries `subnet_id` (token), `availability_zone`, `ipv4_cidr_block`, and `route_table`.

- Default subnet configuration: public subnets route 0.0.0.0/0 to the Internet gateway; private subnets route 0.0.0.0/0 to a NAT gateway; isolated subnets have no default route — instances inside them cannot reach the internet unless you attach another networking path (VPC endpoint, transit gateway, etc.).

### Key CDK Concepts

- The `Vpc` L2 construct is a composite — it orchestrates a nested construct tree of `CfnVPC`, `CfnSubnet`, `CfnRouteTable`, `CfnRoute`, `CfnInternetGateway`, `CfnVPCGatewayAttachment`, `CfnNatGateway`, and `CfnEIP` resources. The logical IDs derive from the construct path, so reordering subnet configuration may cause resource replacement.

- The construct retains a reference to each child subnet construct. You navigate them via typed lists or the `select_subnets()` method, not by iterating over construct children.

- Token resolution: every property that returns a CloudFormation reference behaves as a `Token` at synth time. Use `Fn.ref` or `Fn.get_att` explicitly only when working at the L1 layer — most L2 methods accept and return tokens transparently.

## Cross-Refs

See [[vpc-custom]] for explicit CIDR and subnet configuration.
See [[vpc-endpoints]] for connecting private subnets to AWS services without a NAT gateway.
See [[ec2-basics]] for launching instances into a VPC.
