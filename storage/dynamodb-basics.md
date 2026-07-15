---
tags:
  - storage
---

# DynamoDB Table with GSI and Autoscaling

A DynamoDB table with a composite primary key, a global secondary index for alternate query paths, and provisioned throughput with autoscaling (or on-demand billing for variable workloads).

## Code

```python
from aws_cdk import (
    RemovalPolicy,
    Stack,
    Duration,
    aws_dynamodb as dynamodb,
    aws_applicationautoscaling as scaling,
)
from constructs import Construct


class OrdersStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # On-demand table — no autoscaling needed
        table = dynamodb.Table(
            self,
            "Orders",
            partition_key=dynamodb.Attribute(
                name="customer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="order_date", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Add a GSI for querying by order status
        table.add_global_secondary_index(
            index_name="ByStatus",
            partition_key=dynamodb.Attribute(
                name="status", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="order_date", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Alternative: provisioned table with autoscaling
        provisioned_table = dynamodb.Table(
            self,
            "ProvisionedOrders",
            partition_key=dynamodb.Attribute(
                name="customer_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Enable read autoscaling
        read_scaling = provisioned_table.auto_scale_read_capacity(
            min_capacity=5, max_capacity=100
        )
        read_scaling.scale_on_utilization(
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Enable write autoscaling
        write_scaling = provisioned_table.auto_scale_write_capacity(
            min_capacity=5, max_capacity=100
        )
        write_scaling.scale_on_utilization(
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
```

## What's Happening

- **`BillingMode.PAY_PER_REQUEST`** (on-demand) charges per read/write request with no capacity planning. Autoscaling is disabled because there is no provisioned throughput to scale. Use this for unpredictable workloads, new applications, or when you want zero capacity management. **`BillingMode.PROVISIONED`** requires specifying `read_capacity` and `write_capacity` — CDK then allows enabling autoscaling via `auto_scale_read_capacity` / `auto_scale_write_capacity`.

- **GSI keys** are modeled as separate `Attribute` definitions. The partition key and optional sort key of a GSI are independent of the table's primary key. Each GSI incurs additional storage and write capacity costs (for provisioning the index), and its throughput is consumed from the table's provisioned capacity or on-demand pool depending on the billing mode.

- **`RemovalPolicy.DESTROY` on a table with data:** CDK will generate the CloudFormation template that deletes the table, and CloudFormation will delete it even if it contains data — unlike S3 buckets which require explicit emptying. There is no built-in `auto_delete_objects` equivalent. If you need to preserve data, use `RemovalPolicy.RETAIN` and handle cleanup separately.

- **`TableV2`** (Global Tables) is a separate construct in `aws_dynamodb.TableV2` (imported via `aws-cdk-lib/aws-dynamodb`). It creates a DynamoDB global table with multi-region replication, requires `BillingMode.PAY_PER_REQUEST`, and supports replicas via the `.add_replica()` method. Use `Table` for single-region tables and `TableV2` for multi-region active-active setups.

### Key CDK Concepts

- `auto_scale_read_capacity` / `auto_scale_write_capacity` return `IScalableTableAttribute` objects. Calling `scale_on_utilization` on those creates an `AWS::ApplicationAutoScaling::ScalableTarget` and an `AWS::ApplicationAutoScaling::ScalingPolicy` under the hood — these are the L1 CloudFormation resources for DynamoDB autoscaling.
- `add_global_secondary_index` modifies the `AWS::DynamoDB::Table` resource's `GlobalSecondaryIndexes` property. Adding a GSI to an existing table triggers a CloudFormation replacement if the index key schema changes, but adding a new GSI with a new name is an in-place update.
- `ProjectionType.ALL` copies all table attributes into the index. `KEYS_ONLY` reduces storage cost. `INCLUDE` lets you specify a subset — useful for covering queries without fetching from the main table.

## Cross-Refs

See [[async-pipeline-s3-sqs-lambda-ddb]] for a complete S3→SQS→Lambda→DynamoDB workflow.
See [[iam-roles-and-grants]] for fine-grained access control to DynamoDB tables.
