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

import { App, CfnOutput, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dotenv from "dotenv";
import * as path from "path";

import { ApiConstruct } from "../lib/api/api-stack";
import { ConnectorConstruct } from "../lib/connector/connector-stack";
import { DynamoDBConstruct } from "../lib/db/dynamodb";
import { EtlStack } from "../lib/etl/etl-stack";
import { AssetsConstruct } from "../lib/model/assets-stack";
import { LLMStack } from "../lib/model/llm-stack";
import { BuildConfig } from "../lib/shared/build-config";
import { DeploymentParameters } from "../lib/shared/cdk-parameters";
import { VpcConstruct } from "../lib/shared/vpc-stack";
import { IAMHelper } from "../lib/shared/iam-helper";
import { AOSConstruct } from "../lib/vector-store/os-stack";
import { PortalConstruct } from "../lib/ui/ui-portal";
import { UiExportsConstruct } from "../lib/ui/ui-exports";
import { UserConstruct } from "../lib/user/user-stack";

dotenv.config();

export class RootStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);
    this.templateOptions.description = "(SO8034) - Intelli-Agent";

    this.setBuildConfig();

    const cdkParameters = new DeploymentParameters(this);
    const iamHelper = new IAMHelper(this, "iam-helper");

    const assetConstruct = new AssetsConstruct(this, "assets-construct", {
      s3ModelAssets: cdkParameters.s3ModelAssets.valueAsString,
      env: process.env,
    });
    const llmStack = new LLMStack(this, "rag-stack", {
      s3ModelAssets: cdkParameters.s3ModelAssets.valueAsString,
      embeddingAndRerankerModelPrefix: assetConstruct.embeddingAndRerankerModelPrefix,
      embeddingAndRerankerModelVersion: assetConstruct.embeddingAndRerankerModelVersion,
      instructModelPrefix: assetConstruct.instructModelPrefix,
      instructModelVersion: assetConstruct.instructModelVersion,
      iamHelper: iamHelper,
      env: process.env,
    });
    llmStack.node.addDependency(assetConstruct);

    const vpcConstruct = new VpcConstruct(this, "vpc-construct");

    const aosConstruct = new AOSConstruct(this, "aos-construct", {
      osVpc: vpcConstruct.connectorVpc,
      securityGroup: vpcConstruct.securityGroup,
    });
    aosConstruct.node.addDependency(vpcConstruct);

    const dynamoDBConstruct = new DynamoDBConstruct(this, "ddb-construct");

    const etlStack = new EtlStack(this, "etl-stack", {
      domainEndpoint: aosConstruct.domainEndpoint || "",
      embeddingAndRerankerEndPoint: llmStack.embeddingAndRerankerEndPoint,
      region: props.env?.region || "us-east-1",
      subEmail: cdkParameters.subEmail.valueAsString ?? "",
      etlVpc: vpcConstruct.connectorVpc,
      subnets: vpcConstruct.privateSubnets,
      securityGroups: vpcConstruct.securityGroup,
      s3ModelAssets: cdkParameters.s3ModelAssets.valueAsString,
      openSearchIndex: cdkParameters.openSearchIndex.valueAsString,
      imageName: cdkParameters.etlImageName.valueAsString,
      etlTag: cdkParameters.etlImageTag.valueAsString,
      iamHelper: iamHelper,
    });
    etlStack.node.addDependency(vpcConstruct);
    etlStack.node.addDependency(aosConstruct);
    etlStack.addDependency(llmStack);

    const connectorConstruct = new ConnectorConstruct(this, "connector-construct", {
      connectorVpc: vpcConstruct.connectorVpc,
      securityGroup: vpcConstruct.securityGroup,
      domainEndpoint: aosConstruct.domainEndpoint || "",
      embeddingEndPoints: [llmStack.embeddingAndRerankerEndPoint],
      openSearchIndex: cdkParameters.openSearchIndex.valueAsString,
      openSearchIndexDict: cdkParameters.openSearchIndexDict.valueAsString,
      env: process.env,
    });
    connectorConstruct.node.addDependency(vpcConstruct);
    connectorConstruct.node.addDependency(aosConstruct);
    connectorConstruct.node.addDependency(llmStack);

    const uiPortal = new PortalConstruct(this, "ui-construct");

    const userConstruct = new UserConstruct(this, "user", {
      adminEmail: cdkParameters.subEmail.valueAsString,
      callbackUrl: uiPortal.portalUrl,
    });

    const apiConstruct = new ApiConstruct(this, "api-construct", {
      apiVpc: vpcConstruct.connectorVpc,
      securityGroup: vpcConstruct.securityGroup,
      domainEndpoint: aosConstruct.domainEndpoint || "",
      embeddingAndRerankerEndPoint: llmStack.embeddingAndRerankerEndPoint || "",
      llmModelId: BuildConfig.LLM_MODEL_ID,
      instructEndPoint:
        BuildConfig.LLM_ENDPOINT_NAME !== ""
          ? BuildConfig.LLM_ENDPOINT_NAME
          : llmStack.instructEndPoint,
      sessionsTableName: dynamoDBConstruct.sessionTableName,
      messagesTableName: dynamoDBConstruct.messageTableName,
      workspaceTableName: etlStack.workspaceTableName,
      sfnOutput: etlStack.sfnOutput,
      openSearchIndex: cdkParameters.openSearchIndex.valueAsString,
      openSearchIndexDict: cdkParameters.openSearchIndexDict.valueAsString,
      jobName: connectorConstruct.jobName,
      jobQueueArn: connectorConstruct.jobQueueArn,
      jobDefinitionArn: connectorConstruct.jobDefinitionArn,
      etlEndpoint: etlStack.etlEndpoint,
      resBucketName: etlStack.resBucketName,
      executionTableName: etlStack.executionTableName,
      etlObjTableName: etlStack.etlObjTableName,
      etlObjIndexName: etlStack.etlObjIndexName,
      env: process.env,
      userPool: userConstruct.userPool,
      userPoolClientId: userConstruct.oidcClientId,
      iamHelper: iamHelper,
    });
    apiConstruct.node.addDependency(vpcConstruct);
    apiConstruct.node.addDependency(aosConstruct);
    apiConstruct.node.addDependency(llmStack);
    apiConstruct.node.addDependency(connectorConstruct);
    apiConstruct.node.addDependency(etlStack);

    const uiExports = new UiExportsConstruct(this, "ui-exports", {
      portalBucket: uiPortal.portalBucket,
      uiProps: {
        websocket: apiConstruct.wsEndpoint,
        apiUrl: apiConstruct.apiEndpoint,
        oidcIssuer: userConstruct.oidcIssuer,
        oidcClientId: userConstruct.oidcClientId,
        oidcLogoutUrl: userConstruct.oidcLogoutUrl,
        oidcRedirectUrl: `https://${uiPortal.portalUrl}/signin`,
      },
    });
    uiExports.node.addDependency(uiPortal);

    new CfnOutput(this, "AOS Index Dict", {
      value: cdkParameters.openSearchIndexDict.valueAsString,
    });
    new CfnOutput(this, "API Endpoint Address", {
      value: apiConstruct.apiEndpoint,
    });
    new CfnOutput(this, "Chunk Bucket", { value: etlStack.resBucketName });
    new CfnOutput(this, "Document Bucket", { value: apiConstruct.documentBucket });
    new CfnOutput(this, "Embedding and Rerank Endpoint", {
      value: llmStack.embeddingAndRerankerEndPoint || "No Embedding Endpoint Created",
    });
    new CfnOutput(this, "ETL Object Table", {
      value: etlStack.etlObjTableName,
    });
    new CfnOutput(this, "Execution Table", {
      value: etlStack.executionTableName,
    });
    new CfnOutput(this, "Glue Job Name", { value: etlStack.jobName });
    new CfnOutput(this, "Instruct Model Endpoint", {
      value: llmStack.instructEndPoint || "No Instruct Endpoint Created",
    });
    new CfnOutput(this, "OpenSearch Endpoint", {
      value: aosConstruct.domainEndpoint || "No OpenSearch Endpoint Created",
    });
    new CfnOutput(this, "VPC", { value: vpcConstruct.connectorVpc.vpcId });
    new CfnOutput(this, "WebPortalURL", {
      value: uiPortal.portalUrl,
      description: "LLM-Bot web portal url",
    });
    new CfnOutput(this, "WebSocket Endpoint Address", {
      value: apiConstruct.wsEndpoint,
    });
  }

  private setBuildConfig() {
    BuildConfig.DEPLOYMENT_MODE =
      this.node.tryGetContext("DeploymentMode") ?? "ALL";
    BuildConfig.LAYER_PIP_OPTION =
      this.node.tryGetContext("LayerPipOption") ?? "";
    BuildConfig.JOB_PIP_OPTION = this.node.tryGetContext("JobPipOption") ?? "";
    BuildConfig.LLM_MODEL_ID =
      this.node.tryGetContext("LlmModelId") ?? "internlm2-chat-7b";
    BuildConfig.LLM_ENDPOINT_NAME =
      this.node.tryGetContext("LlmEndpointName") ?? "";
  }
}

// For development, use account/region from CDK CLI
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();
new RootStack(app, "intelli-agent", { env: devEnv });
app.synth();
