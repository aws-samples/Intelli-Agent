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
import { SharedConstruct } from "../shared/shared-construct";
import { IAMHelper } from "../shared/iam-helper";

dotenv.config();

export interface ModelStackProps {
  readonly config: SystemConfig;
  readonly sharedConstruct: SharedConstruct;
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

export class ModelConstruct extends Construct {
  public embeddingAndRerankerEndpoint: sagemaker.CfnEndpoint;
  public knowledgeBaseEndpoint: sagemaker.CfnEndpoint;
  public instructEndpoint: string = "";

  private iamHelper: IAMHelper;
  private account = Aws.ACCOUNT_ID;
  private region = Aws.REGION;
  private executionRole: iam.Role;

  constructor(scope: Construct, id: string, props: ModelStackProps) {
    super(scope, id);

    this.iamHelper = props.sharedConstruct.iamHelper;

    const modelImageUrlDomain =
      this.region === "cn-north-1" || this.region === "cn-northwest-1"
        ? ".amazonaws.com.cn/"
        : ".amazonaws.com/";

    const modelPublicEcrAccount =
      this.region === "cn-north-1" || this.region === "cn-northwest-1"
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

    this.executionRole = executionRole;

    // Deploy Embedding and Reranker model
    let embeddingAndRerankerModelPrefix = props.config.model.embeddingsModels.find(
      (model) => model.default === true,
    )?.name ?? "";
    let embeddingAndRerankerModelVersion = props.config.model.embeddingsModels.find(
      (model) => model.default === true,
    )?.commitId ?? "";
    let embeddingAndRerankerModelName = embeddingAndRerankerModelPrefix + "-" + embeddingAndRerankerModelVersion.slice(0, 5)
    let embeddingAndRerankerImageUrl = modelPublicEcrAccount + this.region + modelImageUrlDomain + "djl-inference:0.21.0-deepspeed0.8.3-cu117";
    let embeddingAndRerankerModelDataUrl = `s3://${props.config.model.modelConfig.modelAssetsBucket}/${embeddingAndRerankerModelPrefix}_deploy_code/`;
    let codePrefix = embeddingAndRerankerModelPrefix + "_deploy_code";

    const embeddingAndRerankerModelResources = this.deploySagemakerEndpoint({
      modelProps: {
        modelName: embeddingAndRerankerModelName,
        executionRoleArn: executionRole.roleArn,
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
            variantName: "variantProd",
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: "ml.g4dn.4xlarge",
          },
        ],
      },
      endpointProps: {
        endpointName: embeddingAndRerankerModelName + "-endpoint",
        endpointConfigName: embeddingAndRerankerModelName + "-endpoint-config",
        tags: [
          {
            key: "version",
            value: embeddingAndRerankerModelVersion,
          }
        ]
      },
    });

    this.embeddingAndRerankerEndpoint = embeddingAndRerankerModelResources.endpoint;


    // Deploy Knowledge Base model
    let knowledgeBaseModelName = "knowledge-base-model";
    let knowledgeBaseModelEcrRepository = props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrRepository;
    let knowledgeBaseModelEcrImageTag = props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrImageTag;
    let knowledgeBaseModelImageUrl = this.account + ".dkr.ecr." + this.region + modelImageUrlDomain + knowledgeBaseModelEcrRepository + ":" + knowledgeBaseModelEcrImageTag;
    let knowledgeBaseVariantName = "variantProd";

    const knowledgeBaseModelResources = this.deploySagemakerEndpoint({
      modelProps: {
        modelName: knowledgeBaseModelName,
        primaryContainer: {
          image: knowledgeBaseModelImageUrl,
        },
        executionRoleArn: executionRole.roleArn,
      },
      endpointConfigProps: {
        endpointConfigName: knowledgeBaseModelName + "-endpoint-config",
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: knowledgeBaseModelName,
            variantName: knowledgeBaseVariantName,
            containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
            initialInstanceCount: 1,
            instanceType: "ml.g4dn.2xlarge",
          },
        ],
        asyncInferenceConfig: {
          clientConfig: {
            maxConcurrentInvocationsPerInstance: 1,
          },
          outputConfig: {
            s3OutputPath: `s3://${props.sharedConstruct.resultBucket.bucketName}/${knowledgeBaseModelName}/`,
          },
        },
      },
      endpointProps: {
        endpointName: knowledgeBaseModelName + "-endpoint",
        endpointConfigName: knowledgeBaseModelName + "-endpoint-config",
      },
    });

    this.knowledgeBaseEndpoint = knowledgeBaseModelResources.endpoint;

    this.createKnowledgeBaseEndpointScaling(this.knowledgeBaseEndpoint, knowledgeBaseVariantName);

  }

  private deploySagemakerEndpoint(props: BuildSagemakerEndpointProps): DeploySagemakerEndpointResponse {
    let model: sagemaker.CfnModel;
    let endpointConfig: sagemaker.CfnEndpointConfig;
    let endpoint: sagemaker.CfnEndpoint;
    let sagemakerRole: iam.Role;

    // Create Sagemaker's model, endpointConfig, and endpoint
    if (props.modelProps) {
      sagemakerRole = this.executionRole;

      // Create Sagemaker Model
      model = new sagemaker.CfnModel(this, `${props.modelProps.modelName}`, props.modelProps);
      // Create Sagemaker EndpointConfig
      endpointConfig = new sagemaker.CfnEndpointConfig(this, `${props.modelProps.modelName}-endpoint-config`, props.endpointConfigProps);
      console.log("EndpointConfigName: ");
      console.log(endpointConfig.endpointConfigName);
      // Add dependency on model
      endpointConfig.addDependency(model);
      // Create Sagemaker Endpoint
      endpoint = new sagemaker.CfnEndpoint(this, `${props.modelProps.modelName}-endpoint`, props.endpointProps);
      // Add dependency on EndpointConfig
      endpoint.addDependency(endpointConfig);

      return { endpoint, endpointConfig, model };
    } else {
      throw Error('You need to provide at least modelProps to create Sagemaker Endpoint');
    }
  }

  private createKnowledgeBaseEndpointScaling(endpoint: sagemaker.CfnEndpoint, variantName: string) {
    const scalingTarget = new appAutoscaling.ScalableTarget(
      this,
      "ETLAutoScalingTarget",
      {
        minCapacity: 0,
        maxCapacity: 10,
        resourceId: `endpoint/${endpoint.endpointName}/variant/${variantName}`,
        scalableDimension: "sagemaker:variant:DesiredInstanceCount",
        serviceNamespace: appAutoscaling.ServiceNamespace.SAGEMAKER,
      }
    );
    scalingTarget.node.addDependency(endpoint);
    scalingTarget.scaleToTrackMetric("ApproximateBacklogSizePerInstanceTrackMetric", {
      targetValue: 2,
      customMetric: new Metric({
        metricName: "ApproximateBacklogSizePerInstance",
        namespace: "AWS/SageMaker",
        dimensionsMap: {
          EndpointName: endpoint.endpointName || "",
        },
        period: Duration.minutes(1),
        statistic: "avg",
      }),
      scaleInCooldown: Duration.seconds(60),
      scaleOutCooldown: Duration.seconds(60),
    });

    // Custom resource to update ETL endpoint autoscaling setting
    const crLambda = new Function(this, "ETLCustomResource", {
      runtime: Runtime.PYTHON_3_11,
      code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
      handler: "etl_custom_resource.lambda_handler",
      environment: {
        ENDPOINT_NAME: endpoint.endpointName || "",
        VARIANT_NAME: variantName
      },
      memorySize: 512,
      timeout: Duration.seconds(300),
    });
    crLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "sagemaker:UpdateEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:DescribeEndpointConfig",
          "sagemaker:UpdateEndpointWeightsAndCapacities",
        ],
        effect: iam.Effect.ALLOW,
        resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/${endpoint.endpointName}`],
      }),
    );
    crLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "application-autoscaling:PutScalingPolicy",
          "application-autoscaling:RegisterScalableTarget",
          "iam:CreateServiceLinkedRole",
          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DeleteAlarms",
        ],
        effect: iam.Effect.ALLOW,
        resources: ["*"],
      }),
    );
    crLambda.node.addDependency(scalingTarget);
    const customResourceProvider = new cr.Provider(this, 'CustomResourceProvider', {
      onEventHandler: crLambda,
      logRetention: logs.RetentionDays.ONE_DAY,
    });

    new CustomResource(this, 'EtlEndpointCustomResource', {
      serviceToken: customResourceProvider.serviceToken,
      resourceType: "Custom::ETLEndpoint",
    });
  }

}
