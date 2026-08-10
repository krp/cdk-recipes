# CDK Recipes

A progressive collection of AWS CDK snippets in Python. Each file demonstrates one CDK pattern with annotated code and explanation of what CDK is doing under the hood.

**Audience**: Experienced Python developers who know AWS services and want to understand CDK's construct model, token system, synthesis, grants, aspects, and deployment patterns.

**Prerequisites**: CDK v2, Python 3.10+, AWS account bootstrapped (`cdk bootstrap`).

---

## Foundation

| File | What it covers |
|------|----------------|
| [[foundations/hello-cdk]] | App, Stack, synth, tokens — the minimal CDK app |
| [[foundations/your-first-bucket]] | L2 construct, logical IDs, RemovalPolicy, physical names |
| [[foundations/stack-parameters-and-context]] | Context variables, SSM lookups, CfnParameter — synthesis vs deploy-time values |
| [[foundations/environment-context]] | env, Aws.ACCOUNT_ID token, partition awareness, stage-based config |
| [[foundations/multiple-stacks]] | Cross-stack references, Fn::ImportValue, stack dependencies |

## Storage

| File | What it covers |
|------|----------------|
| [[storage/s3-bucket-props]] | Encryption, versioning, lifecycle rules, intelligent-tiering |
| [[storage/s3-static-website]] | S3 website hosting, CloudFront OAI, Route53 alias, BucketDeployment |
| [[storage/cloudfront-oac]] | CloudFront distribution + OAC over a private S3 bucket, CfnOutputs |
| [[storage/s3-event-notifications]] | S3 → SQS/SNS/Lambda event destinations, prefix/suffix filtering |
| [[storage/dynamodb-basics]] | Table keys, GSI, billing modes, autoscaling, removal policy |

## Compute

| File | What it covers |
|------|----------------|
| [[compute/lambda-hello-python]] | Code.from_asset, runtime, handler, asset change detection |
| [[compute/lambda-url]] | FunctionUrl, AWS_IAM auth, CORS, SigV4 |
| [[compute/lambda-layers]] | LayerVersion, path structure, PythonLayerVersion |
| [[compute/lambda-s3-integration]] | S3-triggered Lambda, grant pattern, error handling |
| [[compute/ec2-basics]] | Instance, UserData, SSM, security group defaults |

## Networking

| File | What it covers |
|------|----------------|
| [[networking/vpc-default]] | Default Vpc construct, subnet types, NAT gateway costs |
| [[networking/vpc-custom]] | Custom CIDR, subnet configuration, AZ awareness, cross-AZ NAT |
| [[networking/vpc-endpoints]] | Gateway vs Interface endpoints, Private DNS, cost |

## Containers

| File | What it covers |
|------|----------------|
| [[containers/ecs-fargate-service]] | FargateTaskDefinition, ALB, auto-scaling, ContainerImage.from_registry |
| [[containers/ecs-cdk-docker]] | ContainerImage.from_asset, DockerImageFunction, ECR lifecycle policies |

## Event-Driven

| File | What it covers |
|------|----------------|
| [[event-driven/sns-topic-subscriptions]] | Subscription types, DLQ, filter policies |
| [[event-driven/sqs-queue-patterns]] | DLQ, dead-letter redrive, visibility timeout, FIFO |
| [[event-driven/eventbridge-scheduler]] | CfnSchedule, cron/rate, flexible time windows, L1 patterns |
| [[event-driven/eventbridge-custom-bus]] | Custom bus, Match class, rules, archive, replay, input transformation |
| [[event-driven/async-pipeline-s3-sqs-lambda-ddb]] | End-to-end: S3 → SQS → Lambda → DynamoDB with DLQ |

## API Gateway

| File | What it covers |
|------|----------------|
| [[api-gateway/api-gateway-basics]] | LambdaRestApi proxy, inline Python Lambda, auto-deploy stage |
| [[api-gateway/api-gateway-http-api]] | HttpApi, Lambda integration, CORS, payload version 2.0 |
| [[api-gateway/api-gateway-rest-api]] | RestApi, models, request validation, Cognito authorizer, usage plans |
| [[api-gateway/api-gateway-websocket]] | WebSocketApi, routes, @connections endpoint |

## Step Functions

| File | What it covers |
|------|----------------|
| [[step-functions/step-functions-basics]] | Chain DSL, Pass/Wait/Choice/Map, standard vs express |
| [[step-functions/step-functions-lambda-chain]] | LambdaInvoke, retry/catch, result_path, result_selector |
| [[step-functions/step-functions-callback]] | .waitForTaskToken pattern, external system integration |

## Security

| File | What it covers |
|------|----------------|
| [[security/iam-policy-construction]] | PolicyDocument, PolicyStatement, conditions, Principals |
| [[security/iam-roles-and-grants]] | grant pattern, managed policies, IGrantable, service principals |
| [[security/kms-key-management]] | KMS key, rotation, grants to roles, multi-region |
| [[security/secrets-manager]] | Secret rotation, HostedRotation, grant_read, dynamic references |

## Monitoring

| File | What it covers |
|------|----------------|
| [[monitoring/cloudwatch-alarms]] | Metric factory, Alarm, CompositeAlarm, treat_missing_data |
| [[monitoring/dashboards]] | GraphWidget, AlarmStatusWidget, dashboard JSON synthesis |

## CI/CD

| File | What it covers |
|------|----------------|
| [[ci-cd/cicd-pipeline]] | CodePipeline, self-mutation, ShellStep, Stage, cross-account |

## Advanced Constructs

| File | What it covers |
|------|----------------|
| [[advanced-constructs/custom-constructs]] | Writing your own Construct, extending vs composing, attribute exposure |
| [[advanced-constructs/construct-patterns]] | Grant forwarding, IGrantable, dataclass props, interface segregation |
| [[advanced-constructs/nested-stacks]] | NestedStack, CloudFormation limits, when to use vs multiple stacks |
| [[advanced-constructs/escape-hatches]] | .node.default_child, add_property_override, CfnResource |
| [[advanced-constructs/custom-resources]] | Provider, on_event_handler, async signaling via SQS/SNS |

## Migration & Composition

| File | What it covers |
|------|----------------|
| [[migration-composition/import-existing-resources]] | from_* methods, resource import, context provider caching |
| [[migration-composition/permission-boundaries]] | Aspects for boundary enforcement, cdk bootstrap flag |
| [[migration-composition/multi-account-deployments]] | env per stack, pipeline cross-account, bootstrap prerequisites |

## Testing & Compliance

| File | What it covers |
|------|----------------|
| [[testing-compliance/testing-with-assertions]] | Template.from_stack, has_resource_properties, Match matchers |
| [[testing-compliance/cdk-nag-compliance]] | AwsSolutionsChecks, NagSuppressions, rule packs, CI blocking |

---

## How to use

Each file is a standalone snippet you can drop into a CDK app. Most show only the stack or construct body — you wrap them with:

```python
from aws_cdk import App

app = App()
MyStack(app, "MyStack")
app.synth()
```

To inspect the CloudFormation output: `cdk synth`

To deploy: `cdk deploy`

Files are linked with [[Obsidian wikilinks]] — open this directory as an Obsidian vault to navigate by following links.
