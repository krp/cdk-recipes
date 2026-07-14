---
tags: networking
---

# Custom VPC

A VPC with explicit CIDR, multi-tier subnet configuration, and control over NAT gateway count to manage cost and cross-AZ traffic.

## Code

```python
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2

vpc = ec2.Vpc(self, "CustomVpc",
    ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
    max_azs=2,
    nat_gateways=1,
    subnet_configuration=[
        ec2.SubnetConfiguration(
            name="Public",
            subnet_type=ec2.SubnetType.PUBLIC,
            cidr_mask=24,
        ),
        ec2.SubnetConfiguration(
            name="Private",
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidr_mask=20,
        ),
        ec2.SubnetConfiguration(
            name="Isolated",
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=24,
        ),
    ],
)
```

## What's Happening

- **`IpAddresses.cidr()`** allocates from a static CIDR block (`10.0.0.0/16`). CDK carves subnets from this range using the provided `cidr_mask` values. The alternative `IpAddresses.aws_ipam()` delegates allocation to AWS IPAM, which pulls from a pool you manage externally — use that when VPC CIDRs must not overlap across accounts or environments.

- **`cidr_mask`** controls the subnet prefix length per tier. CDK distributes subnets evenly across AZs. With `10.0.0.0/16`, `max_azs=2`, a `cidr_mask=24` public tier gets two `/24` subnets (one per AZ). A `/20` private tier gets two `/20` subnets. CDK allocates non-overlapping ranges by walking the CIDR block sequentially, starting from the first tier.

- **`PRIVATE_WITH_EGRESS`** creates subnets whose default route points to a NAT gateway — instances reach the internet but are not reachable from it. **`PRIVATE_ISOLATED`** creates subnets with no default route at all: no internet egress, no inbound from outside the VPC. Use isolated for internal databases, internal queues, or any workload that should never talk to the internet.

- **`nat_gateways=1`** creates a single NAT gateway in the first AZ. Private subnets in the other AZ route through it — traffic incurs cross-AZ data transfer charges ($0.01/GB each way). Set `nat_gateways=max_azs` to eliminate cross-AZ NAT traffic at the cost of additional gateway hours.

- **Subnet selection** uses `vpc.select_subnets()`:
  ```python
  private_subnets = vpc.select_subnets(subnet_group_name="Private")
  ```
  Returns a `SelectedSubnets` object containing the filtered `ISubnet` list. Filter by `subnet_group_name` (the `name` from `SubnetConfiguration`), `availability_zone`, `subnet_type`, or `one_per_az`. Use this when launching resources into specific tiers.

- **Routes**: CDK populates route tables based on tier type. Public tier gets `0.0.0.0/0 -> InternetGateway`. Private with egress gets `0.0.0.0/0 -> NatGateway`. Isolated gets only the local VPC route. You can add custom routes with `vpc.add_route()` on the subnet level.

### Key CDK Concepts

- `subnet_configuration` order matters: CDK allocates CIDR blocks in list order. Changing the order or inserting a tier shifts the allocation of every subsequent tier, which causes subnet replacement on existing stacks.

- `PRIVATE_WITH_EGRESS` is the CDK v2 name for what v1 called `PRIVATE` — it makes the egress requirement explicit. `PRIVATE_ISOLATED` was called `ISOLATED` in v1.

- The `Vpc` construct generates logical IDs that incorporate the subnet configuration hash. Any change to `cidr_mask`, `max_azs`, or the tier list is a new logical ID and triggers replacement.

## Cross-Refs

See [[vpc-default]] for the minimal VPC with all defaults.
See [[vpc-endpoints]] for connecting isolated subnets to AWS services without a NAT gateway.
See [[multi-account-deployments]] for sharing a VPC across accounts via Resource Access Manager.
