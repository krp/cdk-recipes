---
tags: compute, lambda
---

# Lambda Function with Python, CDK Bundling, and CloudWatch Logs

A Python Lambda function using CDK's asset bundling via `Code.from_asset()`, with the handler code in a local directory and automatic log group creation.

## Code

```python
from aws_cdk import (
    aws_lambda as lambda_,
    Stack,
)
from constructs import Construct


class HelloStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        lambda_.Function(
            self,
            "HelloHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="hello.handler",
            code=lambda_.Code.from_asset("lambda/hello"),
        )
```

The `lambda/hello/` directory containing the handler:

```python
# lambda/hello/hello.py
import json


def handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello from Lambda"}),
    }
```

```text
# lambda/hello/requirements.txt
# (empty for this example — add boto3, requests, etc. as needed)
```

## What's Happening

- **`Code.from_asset("lambda/hello")`** tells CDK to bundle the entire `lambda/hello` directory as a ZIP archive, upload it to the CDK S3 staging bucket during `cdk synth`, and reference it in the CloudFormation template. CDK watches the asset directory for changes during `cdk watch` and triggers a hotswap deployment when files change.

- **`from_asset()` vs `from_inline()` vs `from_docker_build()`**: `from_inline()` accepts raw Python source as a string — fine for single-file handlers under 4 KB, but loses CDK asset change detection and cannot bundle dependencies. `from_docker_build()` runs a Docker build to produce the deployment artifact, useful when you need system-level dependencies or a specific build environment. `from_asset()` is the standard choice for most Python functions: CDK zips the directory verbatim.

- If you need pip dependency bundling without managing the layer yourself, use `PythonFunction` from `aws-cdk-lib/aws-lambda-python-alpha`. It runs `pip install -r requirements.txt` in a Docker container (or the local environment with `bundling` option) and packages the result into the Lambda deployment ZIP.

- The handler signature `def handler(event, context)` receives the invocation event as the first argument (a dict for JSON payloads, a bytes object for non-JSON) and a `context` object exposing AWS request ID, function name, remaining execution time, and the log stream name. CDK's runtime wrapper handles deserialization and invocation.

- CDK auto-creates a CloudWatch Log Group for the function named `/aws/lambda/<function-name>` with a retention policy inherited from the stack's `termination_protection` or a default `INFINITE` retention. You can override this by creating an explicit `aws_logs.LogGroup` resource in the stack.

### Key CDK Concepts

- **Asset path resolution**: The path `"lambda/hello"` is relative to the CDK app's entry point (usually `app.py`), not the stack file. CDK resolves the asset during synthesis and uploads it to the bootstrap bucket.
- **Runtime selection**: `PYTHON_3_12` resolves to the Python 3.12 managed runtime. Lambda deprecates runtimes on a schedule — specify a concrete runtime rather than relying on defaults.

## Cross-Refs

See [[lambda-layers]] for sharing Python dependencies across functions.
See [[lambda-url]] for adding an HTTPS endpoint to this function.
See [[custom-constructs]] for wrapping the Function + log group into a reusable construct.
