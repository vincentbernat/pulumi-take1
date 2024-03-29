import pulumi
import pulumi_aws as aws


def cloudfront_distribution(domain):
    """Cookie-less Cloudfront distribution."""
    return aws.cloudfront.Distribution(
        domain,
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            allowed_methods=[
                "GET",
                "HEAD",
            ],
            cached_methods=[
                "GET",
                "HEAD",
            ],
            target_origin_id="MyOrigin",
            viewer_protocol_policy="allow-all",
            compress=True,
            min_ttl=0,
            default_ttl=86400,
            max_ttl=31536000,
            forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                # No cookies
                cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                    forward="none",
                    whitelisted_names=[],
                ),
                # Forward the "Accept" header
                headers=["Accept"],
                # No need for the query string
                query_string=False,
            ),
        ),
        enabled=True,
        http_version="http2and3",
        is_ipv6_enabled=True,
        origins=[
            aws.cloudfront.DistributionOriginArgs(
                domain_name=domain,
                origin_id="MyOrigin",
                origin_path="",
                custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_keepalive_timeout=5,
                    origin_protocol_policy="https-only",
                    origin_read_timeout=30,
                    origin_ssl_protocols=["TLSv1.2"],
                ),
            )
        ],
        price_class="PriceClass_All",
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            ),
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,
        ),
    )


cloudfront_distribution("media.bernat.ch")
cloudfront_distribution("media.une-oasis-une-ecole.fr")
