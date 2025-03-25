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

import { Aws, NestedStack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";
import { Construct } from "constructs";
import * as dotenv from "dotenv";
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

export class ModelConstruct extends NestedStack implements ModelConstructOutputs {
  public defaultEmbeddingModelName: string = "";
  public defaultKnowledgeBaseModelName: string = "";
  modelAccount = Aws.ACCOUNT_ID;
  modelRegion: string;
  modelIamHelper: IAMHelper;
  modelExecutionRole?: iam.Role = undefined;
  modelImageUrlDomain?: string;
  modelPublicEcrAccount?: string;
  modelVariantName?: string;

  constructor(scope: Construct, id: string, props: ModelConstructProps) {
    super(scope, id);
    this.modelRegion = props.config.deployRegion;
    this.modelIamHelper = props.sharedConstructOutputs.iamHelper;

    this.initializeSageMakerConfig();
    const embeddingAndRerankerModelResources = this.deployEmbeddingAndRerankerEndpoint(props);

    // handle embedding model name setup
    if (props.config.model.embeddingsModels[0].provider === "Bedrock") {
      this.defaultEmbeddingModelName = props.config.model.embeddingsModels[0].id;
    } else if (props.config.model.embeddingsModels[0].provider === "SageMaker") {
      // Initialize SageMaker-specific configurations

      // // Set up embedding model if it's the BCE+BGE model
      // if (props.config.model.embeddingsModels.some(model => model.id === 'bce-embedding-base_v1') || props.config.model.rerankModels.some(model => model.id === 'bge-reranker-large')) {
      //   const embeddingAndRerankerModelResources = this.deployEmbeddingAndRerankerEndpoint(props);
      //   this.defaultEmbeddingModelName = embeddingAndRerankerModelResources.endpoint.endpointName ?? "";
      // }

      // User must deploy reranker endpoint since bedrock does not support reranker model in us-east-1
      this.defaultEmbeddingModelName = embeddingAndRerankerModelResources.endpoint.endpointName ?? "";
    }

    // Handle knowledge base setup separately
    if (props.config.knowledgeBase.enabled &&
      props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled &&
      props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.enabled) {

      // Initialize SageMaker config if not already done
      if (!this.modelExecutionRole) {
        this.initializeSageMakerConfig();
      }

      // Deploy knowledge base model if enabled
      const knowledgeBaseModelResources = this.deployKnowledgeBaseEndpoint(props);
      this.defaultKnowledgeBaseModelName = knowledgeBaseModelResources.endpoint.endpointName ?? "";
    }

  }

  private deployEmbeddingAndRerankerEndpoint(props: ModelConstructProps) {
    // Deploy Embedding and Reranker model
    let embeddingAndRerankerModelPrefix = "bce-embedding-and-bge-reranker";
    let embeddingAndRerankerModelVersion = "20250325";
    let embeddingAndRerankerEndpointInstanceType = "ml.g4dn.4xlarge";
    let embeddingAndRerankerModelName = embeddingAndRerankerModelPrefix + "-" + embeddingAndRerankerModelVersion;
    let embeddingAndRerankerImageUrl = this.modelPublicEcrAccount + this.modelRegion + this.modelImageUrlDomain + "djl-inference:0.21.0-deepspeed0.8.3-cu117";
    let embeddingAndRerankerModelDataUrl = `s3://${props.config.model.modelConfig.modelAssetsBucket}/bce-embedding-and-bge-reranker_deploy_code/`;
    let codePrefix = embeddingAndRerankerModelPrefix + "_deploy_code";

    const embeddingAndRerankerModelResources = this.deploySagemakerEndpoint({
      modelProps: {
        modelName: embeddingAndRerankerModelName,
        executionRoleArn: this.modelExecutionRole?.roleArn,
        primaryContainer: {
          image: embeddingAndRerankerImageUrl,
          modelDataUrl: embeddingAndRerankerModelDataUrl,
          environment: {
            S3_CODE_PREFIX: codePrefix,
          },
          mode: "MultiModel"
        },
      },
      endpointConfigProps: {
        endpointConfigName: embeddingAndRerankerModelName + "-endpoint-config",
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: embeddingAndRerankerModelName,
            variantName: this.modelVariantName || "",
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: embeddingAndRerankerEndpointInstanceType,
          },
        ],
      },
      endpointProps: {
        endpointName: "bce-embedding-and-bge-reranker-43972-endpoint",
        endpointConfigName: embeddingAndRerankerModelName + "-endpoint-config",
        tags: [
          {
            key: "version",
            value: embeddingAndRerankerModelVersion,
          }
        ]
      },
    });

    return embeddingAndRerankerModelResources;
  }

  private deployKnowledgeBaseEndpoint(props: ModelConstructProps) {
    // Deploy Knowledge Base model
    let knowledgeBaseModelInstanceType = "ml.g4dn.2xlarge";
    let knowledgeBaseModelEcrRepository = props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrRepository;
    let knowledgeBaseModelEcrImageTag = props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrImageTag;
    let knowledgeBaseModelName = "knowledge-base-model" + "-" + knowledgeBaseModelEcrImageTag;
    let knowledgeBaseModelImageUrl = this.modelAccount + ".dkr.ecr." + this.modelRegion + this.modelImageUrlDomain + knowledgeBaseModelEcrRepository + ":" + knowledgeBaseModelEcrImageTag;

    const knowledgeBaseModelResources = this.deploySagemakerEndpoint({
      modelProps: {
        modelName: knowledgeBaseModelName,
        primaryContainer: {
          image: knowledgeBaseModelImageUrl,
        },
        executionRoleArn: this.modelExecutionRole?.roleArn,
      },
      endpointConfigProps: {
        endpointConfigName: knowledgeBaseModelName + "-endpoint-config",
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: knowledgeBaseModelName,
            variantName: this.modelVariantName || "",
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: knowledgeBaseModelInstanceType,
          },
        ],
        asyncInferenceConfig: {
          clientConfig: {
            maxConcurrentInvocationsPerInstance: 1,
          },
          outputConfig: {
            s3OutputPath: `s3://${props.sharedConstructOutputs.resultBucket.bucketName}/${knowledgeBaseModelName}/output`,
            s3FailurePath: `s3://${props.sharedConstructOutputs.resultBucket.bucketName}/${knowledgeBaseModelName}/failure`,
          },
        },
      },
      endpointProps: {
        endpointName: knowledgeBaseModelName + "-endpoint",
        endpointConfigName: knowledgeBaseModelName + "-endpoint-config",
      },
    });

    return knowledgeBaseModelResources;
  }

  private deploySagemakerEndpoint(props: BuildSagemakerEndpointProps): DeploySagemakerEndpointResponse {
    let model: sagemaker.CfnModel;
    let endpointConfig: sagemaker.CfnEndpointConfig;
    let endpoint: sagemaker.CfnEndpoint;
    // let sagemakerRole: iam.Role | undefined;

    // Create Sagemaker's model, endpointConfig, and endpoint
    if (props.modelProps) {
      // sagemakerRole = this.modelExecutionRole;
      // const randomString = Math.random().toString(36).substring(2, 8);
      // const smModelName = `${props.modelProps.modelName}ia-${randomString}`;
      const smModelName = `${props.modelProps.modelName}`;

      // Create Sagemaker Model
      model = new sagemaker.CfnModel(this, smModelName, props.modelProps);
      // model = new sagemaker.CfnModel(this, smModelName, props.modelProps);
      // Create Sagemaker EndpointConfig
      endpointConfig = new sagemaker.CfnEndpointConfig(this, `${smModelName}-endpoint-config`, props.endpointConfigProps);
      // Add dependency on model
      endpointConfig.addDependency(model);
      // Create Sagemaker Endpoint
      endpoint = new sagemaker.CfnEndpoint(this, `${smModelName}-endpoint`, props.endpointProps);
      // Add dependency on EndpointConfig
      endpoint.addDependency(endpointConfig);

      return { endpoint, endpointConfig, model };
    } else {
      throw Error('You need to provide at least modelProps to create Sagemaker Endpoint');
    }
  }

  private initializeSageMakerConfig() {
    this.modelVariantName = "variantProd";

    const isChinaRegion = this.modelRegion === "cn-north-1" || this.modelRegion === "cn-northwest-1";

    this.modelImageUrlDomain = isChinaRegion ? ".amazonaws.com.cn/" : ".amazonaws.com/";
    this.modelPublicEcrAccount = isChinaRegion ? "727897471807.dkr.ecr." : "763104351884.dkr.ecr.";

    // Create IAM execution role
    const executionRole = new iam.Role(this, "intelli-agent-endpoint-execution-role", {
      assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchLogsFullAccess"),
      ],
    });

    // Add required policies
    executionRole.addToPolicy(this.modelIamHelper.logStatement);
    executionRole.addToPolicy(this.modelIamHelper.s3Statement);
    executionRole.addToPolicy(this.modelIamHelper.endpointStatement);
    executionRole.addToPolicy(this.modelIamHelper.bedrockStatement);
    executionRole.addToPolicy(this.modelIamHelper.stsStatement);
    executionRole.addToPolicy(this.modelIamHelper.ecrStatement);
    executionRole.addToPolicy(this.modelIamHelper.llmStatement);
    executionRole.addToPolicy(this.modelIamHelper.secretsManagerStatement);
    this.modelExecutionRole = executionRole;
  }

}

