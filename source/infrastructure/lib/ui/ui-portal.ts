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
  aws_iam as iam,
  aws_cloudfront_origins as origins,
} from "aws-cdk-lib";
import { v4 as uuidv4 } from 'uuid';

export interface PortalConstructOutputs {
  portalBucket: s3.Bucket;
  portalUrl: string;
}

export interface PortalConstructProps {
  /**
   * Optional path to the UI source files. Defaults to "../../../portal/dist"
   */
  uiSourcePath?: string;
  responseHeadersPolicyName: string;
}

/**
 * Construct to provision Portal assets and CloudFront Distribution
 */
export class PortalConstruct extends Construct implements PortalConstructOutputs {
  public portalBucket: s3.Bucket;
  public portalUrl: string;

  constructor(scope: Construct, id: string, props: PortalConstructProps) {
    super(scope, id);

    // Create S3 bucket for web assets
    this.portalBucket = new s3.Bucket(this, 'WebsiteBucket', {
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      accessControl: s3.BucketAccessControl.PRIVATE,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.RETAIN,
      autoDeleteObjects: false,
      objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
    });

    // Create Origin Access Identity
    const originAccessIdentity = new cloudfront.OriginAccessIdentity(this, 'OAI');
    originAccessIdentity.applyRemovalPolicy(RemovalPolicy.DESTROY);

    // Grant read permissions to CloudFront
    this.portalBucket.grantRead(originAccessIdentity);
    const oaiId = `origin-access-identity/cloudfront/${originAccessIdentity.originAccessIdentityId}`;

    // Create CloudFront distribution using CfnDistribution
    const distribution = new cloudfront.CfnDistribution(this, 'Distribution', {
      distributionConfig: {
        enabled: true,
        comment: `${Aws.STACK_NAME} portal (${Aws.REGION})`,
        defaultRootObject: 'index.html',
        priceClass: 'PriceClass_All',
        ipv6Enabled: false,
        origins: [
          {
            id: this.portalBucket.bucketName,
            domainName: this.portalBucket.bucketRegionalDomainName,
            s3OriginConfig: {
              originAccessIdentity: oaiId,
            },
          }
        ],
        defaultCacheBehavior: {
          targetOriginId: this.portalBucket.bucketName,
          viewerProtocolPolicy: 'redirect-to-https',
          compress: true,
          forwardedValues: {
            queryString: false,
            cookies: { forward: 'none' }
          },
          minTtl: 0,
          defaultTtl: 86400,
          maxTtl: 31536000,
        },
        customErrorResponses: [
          {
            errorCode: 403,
            responseCode: 200,
            responsePagePath: '/index.html',
          },
          {
            errorCode: 404,
            responseCode: 200,
            responsePagePath: '/index.html',
          }
        ],
        httpVersion: 'http2',
      }
    });

    this.portalUrl = `${distribution.attrDomainName}`;

    // Use provided source path or fall back to default
    const uiSourcePath = props.uiSourcePath || path.join(__dirname, "../../../portal/dist");

    // Upload static web assets
    new s3d.BucketDeployment(this, "DeployWebAssets", {
      sources: [s3d.Source.asset(uiSourcePath)],
      destinationBucket: this.portalBucket,
      distribution: cloudfront.Distribution.fromDistributionAttributes(this, 'ImportedDist', {
        distributionId: distribution.attrId,
        domainName: distribution.attrDomainName
      }),
      distributionPaths: ['/*'],
      prune: false,
    });
  }
}

