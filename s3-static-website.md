---
tags: storage
---

# S3 Static Website with CloudFront OAI and Route53

An S3-backed static website fronted by CloudFront with an origin access identity restricting access to the CDN only, plus a Route53 alias record for custom domain routing.

## Code

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from constructs import Construct


class StaticSiteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Bucket configured for website hosting
        site_bucket = s3.Bucket(
            self,
            "Site",
            website_index_html="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS,
        )

        # CloudFront OAI — only CloudFront can read objects
        origin_access_identity = cloudfront.OriginAccessIdentity(
            self,
            "SiteOAI",
            comment=f"OAI for {site_bucket.bucket_name}",
        )
        site_bucket.grant_read(origin_access_identity)

        distribution = cloudfront.Distribution(
            self,
            "SiteDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    site_bucket,
                    origin_access_identity=origin_access_identity,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            domain_names=["example.com"],
            certificate=None,  # reference an ACM certificate via aws_cdk.aws_certificatemanager
        )

        # Route53 alias — resolves example.com to CloudFront
        zone = route53.HostedZone.from_lookup(self, "Zone", domain_name="example.com")
        route53.ARecord(
            self,
            "SiteAlias",
            zone=zone,
            record_name="example.com",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(distribution)
            ),
        )

        # Deploy local assets to the bucket
        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset("./site-contents")],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )
```

## What's Happening

- **`website_index_html="index.html"`** enables S3's website hosting endpoint (`http://<bucket>.s3-website-<region>.amazonaws.com`), not the REST API endpoint. These are different: the website endpoint supports only HTTP `GET`/`HEAD` and serves static website behavior (index documents, error documents, redirects). The REST endpoint supports all S3 operations but does not serve index documents.

- **`public_read_access=True` with `block_public_access=BlockPublicAccess.BLOCK_ACLS`** makes objects publicly readable for the website endpoint, but still blocks ACL-based public access. This is a compromise — the website endpoint cannot use OAI-based access control, so the bucket objects themselves must be readable. The pattern shown uses OAI on the CloudFront side (which reads from the REST endpoint), so `public_read_access` on the bucket is only needed if CloudFront is configured to use the website endpoint as origin instead.

- **CloudFront OAI** (origin access identity) is a special CloudFront user that S3 bucket policies can grant read access to. The `grant_read(origin_access_identity)` call creates a bucket policy that allows only that OAI to `s3:GetObject`. This is the recommended pattern: CloudFront is the only public-facing entry point; direct S3 access is denied.

- **`BucketDeployment`** from `aws-s3-deployment` is an L2 construct that creates a custom resource (Lambda) to copy local files to the bucket on deployment or when files change. It can optionally invalidate CloudFront cache paths via the `distribution` and `distribution_paths` properties.

- **Why `public_read_access` alone is dangerous**: enabling it without a restrictive `block_public_access` leaves the bucket open to anyone who discovers the S3 URL. Attackers scan for open buckets. The OAI pattern means you can keep `block_public_access=BlockPublicAccess.BLOCK_ALL` and grant only the OAI's `s3:GetObject` permission via a bucket policy — no public access at all.

### Key CDK Concepts

- `origins.S3Origin` wraps both the bucket reference and the OAI into a single CloudFront origin definition — it generates the origin configuration and the necessary bucket policy statement.
- `HostedZone.from_lookup` performs a DNS lookup at synthesis time to resolve the hosted zone ID — the zone must exist in the same AWS account.
- `BucketDeployment` uses the `aws-s3-deployment` submodule, which has a separate npm/PyPI dependency — import from `aws_cdk.aws_s3_deployment`, not from `aws_s3`.

## Cross-Refs

See [[s3-bucket-props]] for general bucket configuration patterns.
See [[api-gateway-http-api]] for when a REST API is the right serving layer instead of S3.
