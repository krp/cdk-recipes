---
tags: compute, lambda, api-gateway
---

# Lambda Function URL

A Lambda function with a direct HTTPS endpoint via `FunctionUrl`, eliminating the need for API Gateway.

## Code

```python
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_lambda as lambda_,
)
from constructs import Construct


class UrlStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_.Function(
            self,
            "MyFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n"
                '    return {"statusCode": 200, "body": "ok"}\n'
            ),
        )

        fn_url = fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.AWS_IAM,
        )

        CfnOutput(self, "Url", value=fn_url.url)
```

## What's Happening

- **`add_function_url()`** is a method on the `Function` L2 construct that provisions a `AWS::Lambda::Url` resource — a dedicated HTTPS endpoint specific to this function. The URL format is `https://<url-id>.lambda-url.<region>.on.aws/`.

- **`AWS_IAM` auth** requires every request to be signed with AWS Signature V4 (SigV4) using an IAM principal's credentials. The caller must have `lambda:InvokeFunctionUrl` permission on the function. Use `IAM` auth for programmatic access from other AWS services or applications that can sign requests.

- **`NONE` auth** makes the URL publicly accessible — anyone with the URL can invoke the function. No sigv4 signing is required. Use this only when you need unauthenticated access (webhooks, public API endpoints) and accept that the endpoint is fully open.

- The `url` property is a CDK **token** (a `{ "Fn::GetAtt": ... }` intrinsic) — it does not resolve to a string until CloudFormation creates the resource. You can use it in `CfnOutput` to display the URL after deployment, or pass it to other constructs.

- CORS configuration is available via the `cors` parameter:
  ```python
  fn.add_function_url(
      auth_type=lambda_.FunctionUrlAuthType.NONE,
      cors=lambda_.FunctionUrlCorsOptions(
          allowed_origins=["https://example.com"],
          allowed_methods=[lambda_.HttpMethod.ALL],
      ),
  )
  ```

- **Limitations**: Function URLs support a maximum 6 MB synchronous payload (request + response), cannot use custom domain names with Route53 or ACM, and lack API Gateway features like request validation, usage plans, or WAF integration. For any of those, use API Gateway HTTP API or REST API.

### Key CDK Concepts

- `add_function_url()` returns a `FunctionUrl` construct — not a string. The `.url` property is the token you use in outputs and references.
- Auth type is set at the construct level — you cannot mix auth types on a single function URL. To change auth, create a new function URL (the old one must be destroyed).
- The function's resource-based policy is updated automatically when you add a function URL with `AWS_IAM` auth.

## Cross-Refs

See [[lambda-hello-python]] for creating the Lambda function itself.
See [[api-gateway-http-api]] when you need custom domains, request validation, or higher payload limits.
