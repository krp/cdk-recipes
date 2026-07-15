---
tags:
  - api-gateway
  - compute
---

# API Gateway HTTP API

A lightweight HTTP API (API Gateway v2) with a Lambda integration, CORS preflight, and automatic stage deployment.

## Code

```python
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_lambda as lambda_,
)
from constructs import Construct


class HttpApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Backend Lambda function
        items_fn = lambda_.Function(
            self,
            "ItemsFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": \'["ok"]\'}\n'
            ),
        )

        # HTTP API with CORS — generates OPTIONS route automatically
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                ],
            ),
        )

        # L2 method wrapping CfnRoute + CfnIntegration + CfnRouteResponse
        http_api.add_routes(
            path="/items",
            methods=[apigwv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration(
                "ItemsIntegration", handler=items_fn
            ),
        )

        CfnOutput(self, "Url", value=http_api.url)
```

## What's Happening

- **`HttpApi` vs `RestApi`:** HTTP API (v2) is simpler, cheaper (~$1/million requests vs ~$3.50), and natively supports OIDC and JWT authorizers. REST API (v1) offers usage plans, request validation models, and Cognito user pool authorizers. Choose HTTP API unless you need v1-specific features.

- **`HttpLambdaIntegration`:** The CDK construct handles two things: it grants `lambda:InvokeFunction` permission to API Gateway on the Lambda resource policy, and it creates the `AWS::ApiGatewayV2::Integration` resource. No manual `addPermission` call needed.

- **`add_routes()`** is a CDK L2 convenience method. A single call synthesizes to a `AWS::ApiGatewayV2::Route` resource, an `AWS::ApiGatewayV2::Integration` (if no existing integration matches), and optionally a `AWS::ApiGatewayV2::RouteResponse`. You can call it multiple times on the same API to add different paths and methods.

- **`cors_preflight`** configures the `CorsPreflightOptions` and CDK automatically generates an `OPTIONS` route on the `$default` stage with the specified headers. No manual route creation required.

- **Auto-deploy stage:** Every HTTP API has a `$default` stage that is automatically deployed on each update. The `.url` property resolves to `https://<api-id>.execute-api.<region>.amazonaws.com`. You can explicitly create stages with `HttpStage` if you need named stages (e.g., `prod`, `dev`) with different settings.

- **Payload format version 2.0:** HTTP API uses the 2.0 payload format by default. The Lambda event structure differs from REST API v1 — under `event['requestContext']['http']` you get `{ method, path, protocol, sourceIp, userAgent }` instead of the v1 format under `event['requestContext']`. If you need the 1.0 format, pass `payload_format_version=apigwv2.PayloadFormatVersion.VERSION_1_0` on the integration.

### Key CDK Concepts

- `HttpApi.url` is a CDK token (`Fn::GetAtt`) resolved at deployment time, not a runtime string.
- `HttpLambdaIntegration` takes a `handler` (the Lambda function) but does not accept additional integration parameters like request/response transformations — those require a `HttpIntegration` with a custom template.
- Adding routes to a deployed API is safe: `add_routes` updates the existing CloudFormation resource stack without requiring replacement of the API.
- Authorizers (`HttpJwtAuthorizer`, `HttpUserPoolAuthorizer`, `HttpLambdaAuthorizer`) are separate construct instances attached via the `authorizer` parameter on routes — they are not built into the API definition itself.

## Cross-Refs

See [[lambda-url]] for a simpler alternative when you don't need API Gateway features.
See [[api-gateway-rest-api]] for the REST API variant with request validation and usage plans.
See [[lambda-hello-python]] for creating the Lambda function itself.
