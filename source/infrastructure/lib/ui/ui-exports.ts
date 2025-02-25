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
import {
  StackProps,
} from "aws-cdk-lib";
import { AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId } from "aws-cdk-lib/custom-resources";
import { RetentionDays } from "aws-cdk-lib/aws-logs";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";

export interface UIProps extends StackProps {
  readonly websocket: string;
  readonly workspaceWebsocket: string;
  readonly apiUrl: string;
  readonly workspaceApiUrl: string;
  readonly oidcIssuer: string;
  readonly oidcClientId: string;
  readonly oidcLogoutUrl: string;
  readonly oidcRedirectUrl: string;
  readonly kbEnabled: string;
  readonly kbType: string;
  readonly embeddingEndpoint: string;
  // readonly apiKey?: string;
}

export interface UiExportsProps extends StackProps {
  readonly portalBucketName: string;
  readonly uiProps: UIProps;
}

/**
 * Construct to provision Portal assets and CloudFront Distribution
 */
export class UiExportsConstruct extends Construct {

  constructor(scope: Construct, id: string, props: UiExportsProps) {
    super(scope, id);

    const configFile = 'aws-exports.json';
    new AwsCustomResource(this, 'WebConfig', {
      logRetention: RetentionDays.ONE_DAY,
      onCreate: {
        action: 'putObject',
        parameters: {
          Body: JSON.stringify(props.uiProps),
          Bucket: props.portalBucketName,
          CacheControl: 'max-age=0, no-cache, no-store, must-revalidate',
          ContentType: 'application/json',
          Key: configFile,
        },
        service: 'S3',
        physicalResourceId: PhysicalResourceId.of(`config-${Date.now()}`),
      },
      onUpdate: {
        action: 'putObject',
        parameters: {
          Body: JSON.stringify(props.uiProps),
          Bucket: props.portalBucketName,
          CacheControl: 'max-age=0, no-cache, no-store, must-revalidate',
          ContentType: 'application/json',
          Key: configFile,
        },
        service: 'S3',
        physicalResourceId: PhysicalResourceId.of(`config-${Date.now()}`),
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ['s3:PutObject'],
          resources: ["*"]
        })
      ])
    });
  }
}
