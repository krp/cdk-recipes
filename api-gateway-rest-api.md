---
tags:
  - api-gateway
  - security
---

# API Gateway REST API

A REST API (API Gateway v1) with a resource tree, request validation, a JSON schema model, and a Cognito user pool authorizer.

## Code

```python
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as lambda_,
)
from constructs import Construct


class OrdersApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # User pool for the Cognito authorizer
        user_pool = cognito.UserPool(self, "OrdersPool", sign_in_case_sensitive=False)

        # Backend Lambda function
        list_fn = lambda_.Function(
            self,
            "ListFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": \'[]\'}\n'
            ),
        )

        # REST API with automatic deployment
        api = apigw.RestApi(
            self,
            "OrdersApi",
            rest_api_name="Orders Service",
            description="Manages orders",
            deploy=True,
            deploy_options=apigw.StageOptions(stage_name="prod"),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST"],
            ),
        )

        # JSON Schema model for request body validation
        model = apigw.Model(
            self,
            "OrderModel",
            rest_api=api,
            schema=apigw.JsonSchema(
                type=apigw.JsonSchemaType.OBJECT,
                required=["customer_id", "amount"],
                properties={
                    "customer_id": apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                    "amount": apigw.JsonSchema(type=apigw.JsonSchemaType.NUMBER),
                },
            ),
        )

        # Resource tree models the URL path hierarchy
        orders = api.root.add_resource("orders")

        orders.add_method(
            "GET",
            apigw.LambdaIntegration(list_fn),
            request_validator=apigw.RequestValidator(
                self,
                "Validator",
                validate_request_parameters=True,
                validate_request_body=True,
            ),
            request_models={"application/json": model},
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self, "Auth", cognito_user_pools=[user_pool]
            ),
        )

        CfnOutput(self, "Url", value=api.url)
```

## What's Happening

- **`RestApi`** creates three CloudFormation resources: `AWS::ApiGateway::RestApi` (the API definition), `AWS::ApiGateway::Deployment` (a snapshot of the API), and `AWS::ApiGateway::Stage` (a named stage pointing to a deployment). Setting `deploy=True` enables the automatic deployment; `deploy_options` configures the stage.

- **Resource tree:** `api.root.add_resource("orders")` models a path segment in the URL hierarchy. Each call returns an `IResource` that you can chain: `api.root.add_resource("v1").add_resource("orders")` produces `/v1/orders`. The resource path is the concatenation of segments.

- **`add_method()`** creates a bundle of resources: `AWS::ApiGateway::Method` (the HTTP verb + request configuration), `AWS::ApiGateway::Integration` (how the backend is invoked), and `AWS::ApiGateway::MethodResponse` (response status codes and headers). Each parameter you pass (validator, models, authorizer) is linked by reference, not inlined.

- **`LambdaIntegration`** vs alternatives: `LambdaIntegration` calls a Lambda function. `MockIntegration` returns a static response without hitting a backend — useful for testing or early prototyping. `HttpIntegration` forwards the request to any HTTP endpoint. `AwsIntegration` integrates with other AWS services (SQS, SNS, Step Functions) directly.

- **Request validation:** CDK creates a `RequestValidator` as a separate `AWS::ApiGateway::RequestValidator` resource attached to the method. When `validate_request_parameters=True`, API Gateway rejects requests with unexpected query string or header parameters. `validate_request_body=True` validates against the attached `request_models` schema. Invalid requests receive a `400` response without invoking the integration.

- **Model:** `apigw.Model` serializes the `JsonSchema` into the `AWS::ApiGateway::Model` resource's schema property. The model maps to a content type (`application/json`) and is referenced by the method's `request_models`. Models are not automatically mapped to error responses — you must also configure a `400` response on the method's `method_responses` if you want the validation error body returned.

- **Cognito authorizer:** `CognitoUserPoolsAuthorizer` is a reusable construct that creates the `AWS::ApiGateway::Authorizer` resource. The method sets `AuthorizationType.COGNITO` and links the authorizer by `authorizer_id`. The Lambda integration receives `event.requestContext.authorizer.claims` containing the decoded JWT claims. The authorizer is defined once and can be attached to multiple methods.

- **Usage plans and API keys:** Call `api.add_usage_plan("Plan", name="Basic", throttle=..., quota=...)` and attach stages with `add_api_stage(stage=api.deployment_stage)`. Create API keys with `api.add_api_key("Key")` and associate them via `plan.add_api_key(key)`. The stage must have `api_key_source_type=apigw.ApiKeySourceType.AUTHORIZER` or `HEADER` to enforce key checking.

### Key CDK Concepts

- `RestApi.url` is a token resolving to `https://<api-id>.execute-api.<region>.amazonaws.com/<stage>/`. The stage name from `deploy_options` is included in the URL.
- The `LambdaIntegration` construct calls `list_fn.grant_invoke(api)` internally — no separate IAM grant is needed.
- `CognitoUserPoolsAuthorizer` does not validate scopes — use `authorization_scopes` on `add_method()` to require specific OAuth scopes from the Cognito token.
- Adding resources and methods to a deployed REST API creates a new deployment snapshot. CDK manages the deployment hash automatically, but you can pin it with `deploy_options` to avoid unnecessary deployments.
- `default_cors_preflight_options` on `RestApi` adds an `OPTIONS` method to every resource automatically. To override per-resource, set `default_cors_preflight_options` at the resource level instead.

## Cross-Refs

See [[api-gateway-http-api]] for the lighter HTTP API alternative that supports JWT and OIDC natively.
See [[iam-roles-and-grants]] for fine-grained IAM permissions on API Gateway methods.
See [[lambda-hello-python]] for creating the Lambda function.
