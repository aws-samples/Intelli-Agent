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

import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";
import { Construct } from "constructs";
import * as dotenv from "dotenv";

import { SystemConfig } from "../shared/types";
import { SharedConstruct } from "../shared/shared-construct";
import { IAMHelper } from "../shared/iam-helper";

dotenv.config();

export interface ModelStackProps {
  readonly config: SystemConfig;
  readonly sharedConstruct: SharedConstruct;
}

interface SagemakerModelResourcesProps {
  modelName: string;
  modelVersion: string;
  executionRoleArn: string;
  imageUrl: string;
  modelAssetsBucket: string;
  modelDeployMode: string;
  modelInstanceType: string;
}

export class ModelConstruct extends Construct {
  public embeddingAndRerankerEndPointName: string = "";
  public instructEndPoint: string = "";
  private iamHelper: IAMHelper;

  constructor(scope: Construct, id: string, props: ModelStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstruct.iamHelper;

    let modelDeployRegion = process.env.CDK_DEFAULT_REGION;

    const modelImageUrlDomain =
      modelDeployRegion === "cn-north-1" || modelDeployRegion === "cn-northwest-1"
        ? ".amazonaws.com.cn/"
        : ".amazonaws.com/";

    const modelImageUrlAccount =
      modelDeployRegion === "cn-north-1" || modelDeployRegion === "cn-northwest-1"
        ? "727897471807.dkr.ecr."
        : "763104351884.dkr.ecr.";

    // Create IAM execution role
    const executionRole = new iam.Role(this, "intelli-agent-endpoint-execution-role", {
      assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchLogsFullAccess"),
      ],
    });
    executionRole.addToPolicy(this.iamHelper.logStatement);
    executionRole.addToPolicy(this.iamHelper.s3Statement);
    executionRole.addToPolicy(this.iamHelper.endpointStatement);
    executionRole.addToPolicy(this.iamHelper.stsStatement);
    executionRole.addToPolicy(this.iamHelper.ecrStatement);
    executionRole.addToPolicy(this.iamHelper.llmStatement);

    // Deploy Embedding and Reranker model
    let embeddingAndRerankerModelPrefix = props.config.model.embeddingsModels.find(
      (model) => model.default === true,
    )?.name ?? "";
    let embeddingAndRerankerModelVersion = props.config.model.embeddingsModels.find(
      (model) => model.default === true,
    )?.commitId ?? "";
    let embeddingAndRerankerImageUrl = modelImageUrlAccount + modelDeployRegion + modelImageUrlDomain + "djl-inference:0.21.0-deepspeed0.8.3-cu117";

    const embeddingAndRerankerModelResources = this.createModelResources({
      modelName: embeddingAndRerankerModelPrefix,
      modelVersion: embeddingAndRerankerModelVersion,
      executionRoleArn: executionRole.roleArn,
      imageUrl: embeddingAndRerankerImageUrl,
      modelAssetsBucket: props.config.model.modelConfig.modelAssetsBucket,
      modelDeployMode: "MultiModel",
      modelInstanceType: "ml.g4dn.4xlarge",
    });

    this.embeddingAndRerankerEndPointName = embeddingAndRerankerModelResources.endpoint.attrEndpointName;

  }

  private createModelResources(props: SagemakerModelResourcesProps) {
    const {
      modelName,
      modelVersion,
      executionRoleArn,
      imageUrl,
      modelAssetsBucket,
      modelDeployMode,
      modelInstanceType,
    } = props;

    let codePrefix = modelName + "_deploy_code";
    let endpointName = modelName + "-" + modelVersion.slice(0, 5);

    const model = new sagemaker.CfnModel(this, `${modelName}-model`, {
      executionRoleArn: executionRoleArn,
      primaryContainer: {
        image: imageUrl,
        modelDataUrl: `s3://${modelAssetsBucket}/${codePrefix}/`,
        environment: {
          S3_CODE_PREFIX: codePrefix,
        },
        mode: modelDeployMode,
      },
    });

    const endpointConfig = new sagemaker.CfnEndpointConfig(
      this,
      `${modelName}-endpoint-config`,
      {
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: model.attrModelName,
            variantName: "variantProd",
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: modelInstanceType
          },
        ],
      }
    );

    const tag: cdk.CfnTag = {
      key: "version",
      value: modelVersion,
    };

    const endpoint = new sagemaker.CfnEndpoint(
      this,
      `${modelName}-endpoint`,
      {
        endpointConfigName: endpointConfig.attrEndpointConfigName,
        endpointName: endpointName,
        tags: [tag],
      }
    );

    return { model, endpointConfig, endpoint };
  }

}

