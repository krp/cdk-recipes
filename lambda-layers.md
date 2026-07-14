---
tags: compute, lambda
---

# Lambda Layer for Shared Python Dependencies

A Lambda Layer that packages shared Python dependencies (requests, pandas, etc.) and attaches them to a function.

## Code

```python
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
)
from constructs import Construct


class LayerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        layer = lambda_.LayerVersion(
            self,
            "Deps",
            code=lambda_.Code.from_asset("layers/deps"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared requests, pandas",
        )

        fn = lambda_.Function(
            self,
            "Fn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "import requests\n\ndef handler(event, context):\n"
                '    return {"statusCode": 200, "body": requests.__version__}\n'
            ),
            layers=[layer],
        )
```

The required directory structure under `layers/deps/`:

```text
layers/deps/
  python/
    lib/
      python3.12/
        site-packages/
          requests/       # pip install requests -t <path>
          pandas/         # pip install pandas -t <path>
```

Create the layer content by installing packages into the correct path:

```bash
pip install requests pandas -t layers/deps/python/lib/python3.12/site-packages/
```

## What's Happening

- **Layer paths**: Lambda extracts the layer ZIP into `/opt`. The Python runtime automatically adds `/opt/python/lib/python3.12/site-packages` to `sys.path`. The `python/` prefix and the full `lib/python3.12/site-packages/` path are mandatory — Lambda's Python runtime uses the standard site-packages layout.

- **CDK does not build the layer** — you must provide the artifact as a ZIP (via `Code.from_asset()`) or reference an existing layer ARN (via `LayerVersion.from_layer_version_arn()`). The alpha library construct `PythonLayerVersion` from `aws-cdk-lib/aws-lambda-python-alpha` runs `pip install` in a Docker container to produce the layer artifact, managing the directory layout and architecture compatibility automatically.

- **Immutable versions**: Each `LayerVersion` construct synthesizes to a single `AWS::Lambda::LayerVersion` resource. Once published, a layer version is immutable. CDK auto-increments the version number when the asset content changes, creating a new layer version on every deployment that modifies the files.

- **Limits**: Up to 5 layers per function, with a total unzipped size limit of 250 MB across all layers. Layer contents are extracted to `/opt` and count toward the function's `/tmp` (512 MB to 10 GB depending on configuration) and execution environment storage.

### Key CDK Concepts

- `compatible_runtimes` is metadata — Lambda rejects runtime mismatches at invocation time, not at deployment. Setting this correctly prevents runtime compatibility errors.
- `Code.from_asset("layers/deps")` treats the directory as a ZIP source. If the directory contains thousands of files, consider zipping them manually and using `Code.from_asset("layers/deps.zip")` for faster synthesis.
- Layer version ARNs follow the pattern `arn:aws:lambda:<region>:<account-id>:layer:<layer-name>:<version-number>`. The layer name is derived from the construct ID.

## Cross-Refs

See [[lambda-hello-python]] for creating the function that uses this layer.
See [[custom-constructs]] for wrapping the layer + function pattern into a reusable construct.
