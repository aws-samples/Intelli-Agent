/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import { Construct } from "constructs";
import * as path from "path";
import {
  Aws,
  Duration,
  aws_cloudfront as cloudfront,
  aws_s3 as s3,
  aws_s3_deployment as s3d,
  RemovalPolicy,
} from "aws-cdk-lib";
import { CloudFrontToS3 } from "@aws-solutions-constructs/aws-cloudfront-s3";

export interface PortalConstructOutputs {
  portalBucket: s3.Bucket;
  portalUrl: string;
}
/**
 * Construct to provision Portal assets and CloudFront Distribution
 */
export class PortalConstruct extends Construct implements PortalConstructOutputs {
  public portalBucket: s3.Bucket;
  public portalUrl: string;

  constructor(scope: Construct, id: string) {
    super(scope, id);
    const getDefaultBehaviour = () => {
      return {
        responseHeadersPolicy: new cloudfront.ResponseHeadersPolicy(
          this,
          "ResponseHeadersPolicy",
          {
            responseHeadersPolicyName: `SecHdr${Aws.REGION}${Aws.STACK_NAME}`,
            comment: "AI-Customer-Service Security Headers Policy",
            securityHeadersBehavior: {
              contentTypeOptions: { override: true },
              frameOptions: {
                frameOption: cloudfront.HeadersFrameOption.DENY,
                override: true,
              },
              referrerPolicy: {
                referrerPolicy: cloudfront.HeadersReferrerPolicy.NO_REFERRER,
                override: true,
              },
              strictTransportSecurity: {
                accessControlMaxAge: Duration.seconds(600),
                includeSubdomains: true,
                override: true,
              },
              xssProtection: {
                protection: true,
                modeBlock: true,
                override: true,
              },
            },
          },
        ),
      };
    };
    // Use cloudfrontToS3 solution constructs
    const portal = new CloudFrontToS3(this, "UI", {
      bucketProps: {
        versioned: false,
        encryption: s3.BucketEncryption.S3_MANAGED,
        accessControl: s3.BucketAccessControl.PRIVATE,
        enforceSSL: true,
        removalPolicy: RemovalPolicy.RETAIN,
        autoDeleteObjects: false,
        objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      },
      cloudFrontDistributionProps: {
        priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
        minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2019,
        enableIpv6: false,
        comment: `${Aws.STACK_NAME} portal (${Aws.REGION})`,
        enableLogging: true,
        errorResponses: [
          {
            httpStatus: 403,
            responseHttpStatus: 200,
            responsePagePath: "/index.html",
          },
        ],
        defaultBehavior: getDefaultBehaviour(),
      },
      insertHttpSecurityHeaders: false,
      loggingBucketProps: {
        objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      },
      cloudFrontLoggingBucketProps: {
        objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      },
    });

    this.portalBucket = portal.s3Bucket as s3.Bucket;
    this.portalUrl = portal.cloudFrontWebDistribution.distributionDomainName;

    // Upload static web assets
    new s3d.BucketDeployment(this, "DeployWebAssets", {
      sources: [
        s3d.Source.asset(path.join(__dirname, "../../../portal/dist")),
      ],
      destinationBucket: this.portalBucket,
      prune: false,
    });
  }
}
