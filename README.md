# CDK Recipes

A progressive collection of AWS CDK snippets in Python. Each file demonstrates one CDK pattern with annotated code and explanation of what CDK is doing under the hood.

**Audience**: Experienced Python developers who know AWS services and want to understand CDK's construct model, token system, synthesis, grants, aspects, and deployment patterns.

**Prerequisites**: CDK v2, Python 3.10+, AWS account bootstrapped (`cdk bootstrap`).

---

## Foundation

| File | What it covers |
|------|----------------|
| [[hello-cdk]] | App, Stack, synth, tokens — the minimal CDK app |
| [[your-first-bucket]] | L2 construct, logical IDs, RemovalPolicy, physical names |
| [[stack-parameters-and-context]] | Context variables, SSM lookups, CfnParameter — synthesis vs deploy-time values |
| [[environment-context]] | env, Aws.ACCOUNT_ID token, partition awareness, stage-based config |
| [[multiple-stacks]] | Cross-stack references, Fn::ImportValue, stack dependencies |

## Storage

| File | What it covers |
|------|----------------|
| [[s3-bucket-props]] | Encryption, versioning, lifecycle rules, intelligent-tiering |
| [[s3-static-website]] | S3 website hosting, CloudFront OAI, Route53 alias, BucketDeployment |
| [[s3-event-notifications]] | S3 → SQS/SNS/Lambda event destinations, prefix/suffix filtering |
| [[dynamodb-basics]] | Table keys, GSI, billing modes, autoscaling, removal policy |

## Compute

| File | What it covers |
|------|----------------|
| [[lambda-hello-python]] | Code.from_asset, runtime, handler, asset change detection |
| [[lambda-url]] | FunctionUrl, AWS_IAM auth, CORS, SigV4 |
| [[lambda-layers]] | LayerVersion, path structure, PythonLayerVersion |
| [[lambda-s3-integration]] | S3-triggered Lambda, grant pattern, error handling |
| [[ec2-basics]] | Instance, UserData, SSM, security group defaults |

## Networking

| File | What it covers |
|------|----------------|
| [[vpc-default]] | Default Vpc construct, subnet types, NAT gateway costs |
| [[vpc-custom]] | Custom CIDR, subnet configuration, AZ awareness, cross-AZ NAT |
| [[vpc-endpoints]] | Gateway vs Interface endpoints, Private DNS, cost |

## Containers

| File | What it covers |
|------|----------------|
| [[ecs-fargate-service]] | FargateTaskDefinition, ALB, auto-scaling, ContainerImage.from_registry |
| [[ecs-cdk-docker]] | ContainerImage.from_asset, DockerImageFunction, ECR lifecycle policies |

## Event-Driven

| File | What it covers |
|------|----------------|
| [[sns-topic-subscriptions]] | Subscription types, DLQ, filter policies |
| [[sqs-queue-patterns]] | DLQ, dead-letter redrive, visibility timeout, FIFO |
| [[eventbridge-scheduler]] | CfnSchedule, cron/rate, flexible time windows, L1 patterns |
| [[eventbridge-custom-bus]] | Custom bus, Match class, rules, archive, replay, input transformation |
| [[async-pipeline-s3-sqs-lambda-ddb]] | End-to-end: S3 → SQS → Lambda → DynamoDB with DLQ |

## API Gateway

| File | What it covers |
|------|----------------|
| [[api-gateway-http-api]] | HttpApi, Lambda integration, CORS, payload version 2.0 |
| [[api-gateway-rest-api]] | RestApi, models, request validation, Cognito authorizer, usage plans |
| [[api-gateway-websocket]] | WebSocketApi, routes, @connections endpoint |

## Step Functions

| File | What it covers |
|------|----------------|
| [[step-functions-basics]] | Chain DSL, Pass/Wait/Choice/Map, standard vs express |
| [[step-functions-lambda-chain]] | LambdaInvoke, retry/catch, result_path, result_selector |
| [[step-functions-callback]] | .waitForTaskToken pattern, external system integration |

## Security

| File | What it covers |
|------|----------------|
| [[iam-policy-construction]] | PolicyDocument, PolicyStatement, conditions, Principals |
| [[iam-roles-and-grants]] | grant pattern, managed policies, IGrantable, service principals |
| [[kms-key-management]] | KMS key, rotation, grants to roles, multi-region |
| [[secrets-manager]] | Secret rotation, HostedRotation, grant_read, dynamic references |

## Monitoring

| File | What it covers |
|------|----------------|
| [[cloudwatch-alarms]] | Metric factory, Alarm, CompositeAlarm, treat_missing_data |
| [[dashboards]] | GraphWidget, AlarmStatusWidget, dashboard JSON synthesis |

## CI/CD

| File | What it covers |
|------|----------------|
| [[cicd-pipeline]] | CodePipeline, self-mutation, ShellStep, Stage, cross-account |

## Advanced Constructs

| File | What it covers |
|------|----------------|
| [[custom-constructs]] | Writing your own Construct, extending vs composing, attribute exposure |
| [[construct-patterns]] | Grant forwarding, IGrantable, dataclass props, interface segregation |
| [[nested-stacks]] | NestedStack, CloudFormation limits, when to use vs multiple stacks |
| [[escape-hatches]] | .node.default_child, add_property_override, CfnResource |
| [[custom-resources]] | Provider, on_event_handler, async signaling via SQS/SNS |

## Migration & Composition

| File | What it covers |
|------|----------------|
| [[import-existing-resources]] | from_* methods, resource import, context provider caching |
| [[permission-boundaries]] | Aspects for boundary enforcement, cdk bootstrap flag |
| [[multi-account-deployments]] | env per stack, pipeline cross-account, bootstrap prerequisites |

## Testing & Compliance

| File | What it covers |
|------|----------------|
| [[testing-with-assertions]] | Template.from_stack, has_resource_properties, Match matchers |
| [[cdk-nag-compliance]] | AwsSolutionsChecks, NagSuppressions, rule packs, CI blocking |

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
