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

import { Aws, Duration, CustomResource } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";
import { Construct } from "constructs";
import * as dotenv from "dotenv";
import * as appAutoscaling from "aws-cdk-lib/aws-applicationautoscaling";
import { Metric } from 'aws-cdk-lib/aws-cloudwatch';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Architecture, Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import { join } from "path";

import { SystemConfig } from "../shared/types";
import { SharedConstructOutputs } from "../shared/shared-construct";
import { IAMHelper } from "../shared/iam-helper";

dotenv.config();

export interface ModelConstructProps {
  readonly config: SystemConfig;
  readonly sharedConstructOutputs: SharedConstructOutputs;
}

export interface ModelConstructOutputs {
  defaultEmbeddingModelName: string;
  defaultKnowledgeBaseModelName: string;
}

interface BuildSagemakerEndpointProps {
  /**
   * User provided props to create Sagemaker Model
   *
   * @default - None
   */
  readonly modelProps: sagemaker.CfnModelProps | any;
  /**
   * User provided props to create Sagemaker Endpoint Configuration
   *
   * @default - None
   */
  readonly endpointConfigProps: sagemaker.CfnEndpointConfigProps;
  /**
   * User provided props to create Sagemaker Endpoint
   *
   * @default - None
   */
  readonly endpointProps: sagemaker.CfnEndpointProps;
}

interface DeploySagemakerEndpointResponse {
  readonly endpoint: sagemaker.CfnEndpoint,
  readonly endpointConfig?: sagemaker.CfnEndpointConfig,
  readonly model?: sagemaker.CfnModel
}

export class ModelConstruct extends Construct implements ModelConstructOutputs {
  public defaultEmbeddingModelName: string = "";
  public defaultKnowledgeBaseModelName: string = "";

  private account = Aws.ACCOUNT_ID;
  private region = Aws.REGION;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    // this.defaultEmbeddingModelName = "cohere.embed-english-v3"
    this.defaultEmbeddingModelName = "amazon.titan-embed-text-v1"
    this.defaultKnowledgeBaseModelName = "anthropic.claude-3-sonnet-20240229-v1:0"

  }

}

