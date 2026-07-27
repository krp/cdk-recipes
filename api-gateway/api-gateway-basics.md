---
tags:
  - api-gateway
  - compute
---

# API Gateway REST API with a Lambda Proxy

The simplest possible API Gateway REST API: a `LambdaRestApi` proxy integration backed by an inline Python Lambda, with an auto-deployed stage. No CORS, authorizers, models, or usage plans — those are layered on in [[api-gateway-rest-api]].

## Code

```python
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
)
from constructs import Construct


class HelloApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Inline Python Lambda — the API backend
        hello = lambda_.Function(
            self,
            "HelloFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": \'{"message": "hello"}\'}\n'
            ),
        )

        # REST API with a Lambda proxy. One call wires the RestApi, the greedy
        # {proxy+} resource + ANY method, the Lambda integration, the Deployment,
        # and the Stage. proxy=True (the default) routes EVERY method and path.
        api = apigw.LambdaRestApi(
            self,
            "HelloApi",
            handler=hello,
        )

        CfnOutput(self, "Url", value=api.url)
```

## What's Happening

- **`LambdaRestApi`** is the highest-level API Gateway L2 — a single construct call synthesizes the `AWS::ApiGateway::RestApi`, a greedy `{proxy+}` resource with an `ANY` method, the `AWS::ApiGateway::Integration` (Lambda proxy), a `AWS::ApiGateway::Deployment`, and a `AWS::ApiGateway::Stage` named `prod`. It is `RestApi` plus a default proxy integration; for explicit per-path/per-method routing, use `RestApi` + `root.add_resource(...).add_method(...)` (see [[api-gateway-rest-api]]).

- **`proxy=True` (the default)** routes every HTTP method and path to the Lambda. The handler receives the v1 proxy event — `event["httpMethod"]`, `event["path"]`, `event["resource"]`, `event["queryStringParameters"]`, `event["body"]` — and must return `{"statusCode", "body"}` where `body` is a string. Set `proxy=False` if you would rather define resources and methods yourself.

- **`Code.from_inline`** embeds the handler source as a string in the CloudFormation template. Fine for a single-file handler under 4 KB with no third-party dependencies, but it bypasses CDK asset bundling and change detection. For anything beyond the stdlib, use `Code.from_asset` with a local directory (see [[lambda-hello-python]]).

- **Invoke permission is automatic.** `LambdaRestApi` builds a `LambdaIntegration` internally, which calls `hello.grant_invoke(api)` — adding `lambda:InvokeFunction` to the function's resource policy. No manual `add_permission` is needed.

- **Auto-deploy + auto-output.** `deploy=True` (the default) hashes the API model into the Deployment's logical ID, so any change to resources or methods produces a new immutable deployment rather than mutating the existing one. `api.url` is a token resolving to `https://<api-id>.execute-api.<region>.amazonaws.com/prod/`. `RestApi` also emits its own endpoint CloudFormation Output; the explicit `CfnOutput` here just names it `Url`.

### Key CDK Concepts

- `LambdaRestApi` extends `RestApi`, so everything on `RestApi` — usage plans, API keys, custom domain names, resource policy, `add_model` — is available here too. The only thing it adds is the default proxy integration.
- The default endpoint is `EndpointType.EDGE` (CloudFront-fronted). For a Regional or Private API, pass `endpoint_configuration=apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL])`.
- `cloud_watch_role=True` (the default) creates a separate `AWS::IAM::Role` that lets API Gateway publish metrics and access logs to CloudWatch.
- For the cheaper, simpler v2 HTTP API (~$1/M vs ~$3.50/M requests, no resource tree), see [[api-gateway-http-api]]. Prefer HTTP API unless you need REST-only features (usage plans, request-validation models, WAF, mutual TLS).

## Cross-Refs

See [[api-gateway-rest-api]] for the explicit resource tree, methods, request validation, Cognito authorizer, and usage plans.
See [[api-gateway-http-api]] for the lighter v2 HTTP API alternative.
See [[lambda-hello-python]] for `from_asset` vs `from_inline`, bundling, and log groups.
