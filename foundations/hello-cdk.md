---
tags:
  - foundation
---

# Hello CDK

The minimal CDK app — `App`, `Stack`, `synth`, and the CloudFormation template it produces.

## Code

```python
# app.py
from aws_cdk import App, Stack, CfnOutput

class MyStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        CfnOutput(self, "Message", value="hello cdk")

app = App()
MyStack(app, "MyStack")
app.synth()
```

```json
// cdk.json
{ "app": "python app.py" }
```

## What's Happening

Every CDK app starts with an `App` root. Constructs are the building blocks: `MyStack` is a subclass of `Stack`, which is itself a construct. `App` owns the stack; the stack owns its resources.

`app.synth()` compiles the construct tree into one or more CloudFormation templates. CDK is a compiler: Python objects become JSON templates, and tokens (resolvable strings like `CfnOutput` values) are replaced at deploy time by CloudFormation intrinsics such as `{ "Ref": "…" }`. The output of synthesis is a `cdk.out/` directory containing the assembled templates.

The `cdk.json` file tells the CLI how to run the app — here, `python app.py`. When you run `cdk synth`, the CLI invokes that entry point, which triggers synthesis and writes the template to stdout or `cdk.out/`.

### Key CDK Concepts

- **App vs Stack**: The `App` is the top-level container; a `Stack` maps 1:1 to a CloudFormation stack. Every construct belongs to exactly one stack, which determines the CloudFormation resource it becomes.
- **Tokens**: `CfnOutput` accepts a Python string, but CDK wraps it in a `Token`. During synthesis, tokens serialize to CloudFormation intrinsics (`Fn::Join`, `Ref`, `Fn::GetAtt`). At deploy time, CloudFormation resolves them.
- **Synth**: Calling `app.synth()` is mandatory. The CLI calls it implicitly on `cdk synth` and `cdk deploy`.

See [[your-first-bucket]] for the next step: deploying an actual resource.
