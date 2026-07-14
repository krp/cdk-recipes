---
tags: api-gateway, compute
---

# API Gateway WebSocket API

A WebSocket API (API Gateway v2) with `$connect`, `$disconnect`, and `$default` routes, and the `@connections` endpoint pattern for sending messages back to connected clients.

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


class WsApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Lambda functions for each route
        connect_fn = lambda_.Function(
            self,
            "ConnectFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": "connected"}\n'
            ),
        )
        disconnect_fn = lambda_.Function(
            self,
            "DisconnectFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": "disconnected"}\n'
            ),
        )
        default_fn = lambda_.Function(
            self,
            "DefaultFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                "    # event['requestContext']['connectionId'] holds the connection ID\n"
                "    # event['body'] contains the WebSocket message\n"
                '    return {"statusCode": 200, "body": "ok"}\n'
            ),
        )

        # WebSocket API with the three built-in routes
        ws_api = apigwv2.WebSocketApi(
            self,
            "WsApi",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "Connect", connect_fn
                ),
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "Disconnect", disconnect_fn
                ),
            ),
            default_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "Default", default_fn
                ),
            ),
        )

        CfnOutput(self, "Url", value=ws_api.api_endpoint)

        # Handler for sending messages back to clients:
        # endpoint = f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
        # client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)
        # client.post_to_connection(
        #     ConnectionId=event['requestContext']['connectionId'],
        #     Data=json.dumps(payload)
        # )
```

## What's Happening

- **`WebSocketApi`** is the L2 construct for `AWS::ApiGatewayV2::Api` with protocol `WEBSOCKET`. It manages the WebSocket adapter — the API Gateway infrastructure that maintains persistent bidirectional connections between clients and your backend Lambda functions. Each connection is mapped to a `connectionId` that the Lambda receives in the event.

- **Built-in route keys:** WebSocket API defines three special route keys that CDK maps through the constructor parameters:
  - `$connect` — invoked when a client establishes a connection. Return a non-2xx status code to reject the connection. Route key `$connect`.
  - `$disconnect` — invoked when a client disconnects or the connection times out (idle timeout defaults to 10 minutes). Route key `$disconnect`.
  - `$default` — catches any message that does not match a custom route key. Route key `$default`.
  
  Custom routes (e.g., `sendMessage`) are added post-construction with `ws_api.add_route("sendMessage", ...)`.

- **`WebSocketLambdaIntegration`:** CDK grants `lambda:InvokeFunction` permission to the API Gateway service principal and creates the `AWS::ApiGatewayV2::Integration` resource. The integration type is `AWS_PROXY`, so API Gateway forwards the entire request to Lambda and returns the Lambda response to the WebSocket client.

- **`@connections` endpoint:** Lambda functions use the `apigatewaymanagementapi` client to send messages back to connected clients. The endpoint URL is constructed from the event payload:
  ```python
  endpoint = f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
  ```
  The `connectionId` from the event identifies which client to send to. Lambda needs `execute-api:ManageConnections` permission on the API — CDK does not grant this automatically, so you must add it via an IAM policy statement scoped to the API's `arn`.

- **Auto-deploy stage:** Like HTTP API, WebSocket API has a `$default` stage deployed automatically. The `.api_endpoint` property returns `wss://<api-id>.execute-api.<region>.amazonaws.com`. Use `apigwv2.WebSocketStage` if you need named stages.

- **IAM auth:** You can restrict which services invoke the WebSocket backend by setting `credentials_role` on the integration. This is useful when you want only specific IAM principals (cross-account services, specific Lambda functions) to send data through the WebSocket.

### Key CDK Concepts

- `WebSocketApi.api_endpoint` is a CDK token — it resolves to `wss://<api-id>.execute-api.<region>.amazonaws.com` at deployment time.
- `WebSocketRouteOptions` requires an `integration` — the route cannot exist without one. If you want a route that does nothing, create a no-op Lambda integration.
- The `$disconnect` route is not guaranteed to fire: a client crash or network partition may prevent API Gateway from calling it. Design your state cleanup to handle missed disconnect events (e.g., TTLs on connection records in DynamoDB).
- Custom route selection uses the `route_selection_expression` parameter on `WebSocketApi`. The default expression is `$request.body.action` — your client sends `{"action": "sendMessage", "data": ...}` and API Gateway matches against the route key. If you change this expression, update the `add_route()` calls to match your custom selection logic.

## Cross-Refs

See [[api-gateway-http-api]] for the HTTP API variant — the two share the same CloudFormation resource type (`AWS::ApiGatewayV2::Api`) differentiated by the `protocol_type` property.
See [[lambda-hello-python]] for creating the Lambda functions.
