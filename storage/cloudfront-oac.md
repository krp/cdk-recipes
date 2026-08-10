---
tags:
  - storage
  - edge
---

# CloudFront with Origin Access Control (OAC)

Serve objects from a private S3 bucket through CloudFront, locking the bucket to CloudFront-only reads via Origin Access Control (OAC) — no public bucket, no OAI.

## Code

```python
from aws_cdk import CfnOutput
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins

# One call: creates the OriginAccessControl construct, attaches it to the
# origin, AND adds the bucket policy that lets only CloudFront read objects.
# The bucket itself stays fully private.
origin = origins.S3BucketOrigin.with_origin_access_control(output_bucket)

distribution = cloudfront.Distribution(
    self,
    "Distribution",
    default_behavior=cloudfront.BehaviorOptions(
        origin=origin,
        viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    ),
)

# The marker discovers the distribution via these outputs — always export them.
CfnOutput(self, "DistributionId", value=distribution.distribution_id)
CfnOutput(self, "DistributionDomainName", value=distribution.distribution_domain_name)
```

## What's Happening

- **`S3BucketOrigin.with_origin_access_control(bucket)`** does three things in one call:
  1. Creates the `OriginAccessControl` construct (S3 type, SigV4 request signing).
  2. Wires it into the CloudFront origin.
  3. Synthesizes a bucket policy allowing `s3:GetObject` **only to the OAC principal** — direct S3 URLs return 403, the bucket keeps `BlockPublicAccess.BLOCK_ALL`, and cdk-nag stays happy.

- **OAC vs OAI**: OAI (Origin Access Identity) is the legacy mechanism — a CloudFront "user" you grant via bucket policy. OAC is the current mechanism (signed origin requests, no IAM user object) and is what AWS recommends for new distributions. If you see OAI in an old tutorial, you're looking at the outdated pattern.

- **Verify end-to-end**: `curl -I https://<distribution-domain>/<key>` returns `200`. Direct `https://<bucket>.s3.<region>.amazonaws.com/<key>` returns `403`.

- **No public bucket needed**: the bucket policy from `with_origin_access_control` is the only access control — do not enable `public_read_access` or website hosting.

### Key CDK Concepts

- `distribution.distribution_id` and `distribution.distribution_domain_name` are what an external marker reads from CloudFormation outputs — export them with `CfnOutput` or the distribution is undiscoverable.
- `ViewerProtocolPolicy.REDIRECT_TO_HTTPS` forces HTTP → HTTPS at the edge.
- The synthesized bucket policy appears as an `AWS::S3::BucketPolicy` resource on the bucket — you don't write it by hand.

## Cross-Refs

See [[s3-bucket-props]] for bucket hardening (block public access, encryption, SSL).
See [[s3-static-website]] for the legacy OAI + website-hosting pattern (not for private media).
