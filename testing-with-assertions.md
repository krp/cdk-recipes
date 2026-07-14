---
tags: testing, advanced
---

# Testing with Assertions

Validate generated CloudFormation templates in unit tests using the CDK assertions module.

## Code

```python
from aws_cdk import assertions

def test_bucket_encrypted():
    stack = MyStack(app, "Test")
    template = assertions.Template.from_stack(stack)

    # Partial match: only the properties listed are checked
    template.has_resource_properties("AWS::S3::Bucket",
        {"BucketEncryption": assertions.Match.object_like({
            "ServerSideEncryptionConfiguration": [{
                "ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
            }]
        })}
    )

    template.resource_count_is("AWS::S3::Bucket", 1)

# Pre-synthesized template validation — read from cdk.out
template = assertions.Template.from_json(
    json.loads(open("cdk.out/MyStack.template.json").read())
)
```

## What's Happening

- `Template.from_stack()` synthesizes the stack in-memory — no write to disk, no `cdk.out/` directory needed
- `has_resource_properties()` performs partial matching: the dictionary provided is a subset of the actual template properties; extra properties in the template are ignored
- `Match` matchers for fine-grained control: `Match.object_like()` (subset match on nested objects), `Match.any_value()`, `Match.absent()` (property must not exist), `Match.array_with()` (partial array match), `Match.exact()` (strict equality)
- `find_resources()` returns a `dict[str, dict]` of matching resources keyed by logical ID, enabling further programmatic assertions
- `Template.from_json()` validates a pre-synthesized template — useful in CI pipelines that synthesize once and run assertions later, or for asserting against templates generated outside CDK
- Assertions operate at the CloudFormation JSON level — you are testing what CDK generates, not what AWS actually deploys
- Combine with pytest: one assertion function per test for clear failure messages and isolated debugging

### Key CDK Concepts

- Template synthesis during testing does not deploy or validate against AWS — it only runs the CDK framework's synthesis logic to produce the CloudFormation JSON
- `Match` matchers are composable: `Match.object_like({"Key": Match.any_value()})` matches any value for `Key` within a partial object match
- For snapshot testing, use `template.to_json()` to dump the full template and compare with a stored snapshot

Cross-ref: [[cdk-nag-compliance]], [[hello-cdk]]
