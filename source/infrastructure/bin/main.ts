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

import { getConfig } from "./config";
import { SystemConfig } from "../cli/types";
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

export interface RootStackProps extends StackProps {
  readonly config: SystemConfig;
}

export class RootStack extends Stack {
  constructor(scope: Construct, id: string, props: RootStackProps) {
    super(scope, id, props);
    this.templateOptions.description = "(SO8034) - Intelli-Agent";

    this.setBuildConfig();

    const cdkParameters = new DeploymentParameters(this);
    const iamHelper = new IAMHelper(this, "iam-helper");

    const assetConstruct = new AssetsConstruct(this, "assets-construct", {
      s3ModelAssets: cdkParameters.s3ModelAssets.valueAsString,
      env: props.env,
    });
    const llmStack = new LLMStack(this, "rag-stack", {
      s3ModelAssets: cdkParameters.s3ModelAssets.valueAsString,
      embeddingAndRerankerModelPrefix: assetConstruct.embeddingAndRerankerModelPrefix,
      embeddingAndRerankerModelVersion: assetConstruct.embeddingAndRerankerModelVersion,
      instructModelPrefix: assetConstruct.instructModelPrefix,
      instructModelVersion: assetConstruct.instructModelVersion,
      iamHelper: iamHelper,
      env: props.env,
    });
    llmStack.node.addDependency(assetConstruct);

    const vpcConstruct = new VpcConstruct(this, "vpc-construct");

    const aosConstruct = new AOSConstruct(this, "aos-construct", {
      osVpc: vpcConstruct.connectorVpc,
      securityGroup: vpcConstruct.securityGroup,
    });
    aosConstruct.node.addDependency(vpcConstruct);

    const dynamoDBConstruct = new DynamoDBConstruct(this, "ddb-construct");
    const uiPortal = new PortalConstruct(this, "ui-construct");

    const etlStack = new EtlStack(this, "etl-stack", {
      domainEndpoint: aosConstruct.domainEndpoint || "AOSnotcreated",
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
      portalBucket: uiPortal.portalBucket.bucketName,
      iamHelper: iamHelper,
    });
    etlStack.node.addDependency(vpcConstruct);
    etlStack.node.addDependency(aosConstruct);
    etlStack.node.addDependency(uiPortal);
    etlStack.addDependency(llmStack);

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
      promptTableName: dynamoDBConstruct.promptTableName,
      chatbotTableName: etlStack.chatbotTableName,
      sfnOutput: etlStack.sfnOutput,
      openSearchIndex: cdkParameters.openSearchIndex.valueAsString,
      openSearchIndexDict: cdkParameters.openSearchIndexDict.valueAsString,
      etlEndpoint: etlStack.etlEndpoint,
      resBucketName: etlStack.resBucketName,
      executionTableName: etlStack.executionTableName,
      etlObjTableName: etlStack.etlObjTableName,
      etlObjIndexName: etlStack.etlObjIndexName,
      indexTableName: dynamoDBConstruct.indexTableName,
      modelTableName: dynamoDBConstruct.modelTableName,
      env: props.env,
      userPool: userConstruct.userPool,
      userPoolClientId: userConstruct.oidcClientId,
      iamHelper: iamHelper,
    });
    apiConstruct.node.addDependency(vpcConstruct);
    apiConstruct.node.addDependency(aosConstruct);
    apiConstruct.node.addDependency(llmStack);
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

    new CfnOutput(this, "API Endpoint Address", {
      value: apiConstruct.apiEndpoint,
    });
    new CfnOutput(this, "Chunk Bucket", { value: etlStack.resBucketName });
    new CfnOutput(this, "WebPortalURL", {
      value: uiPortal.portalUrl,
      description: "Web portal url",
    });
    new CfnOutput(this, "WebSocket Endpoint Address", {
      value: apiConstruct.wsEndpoint,
    });
    new CfnOutput(this, "OidcClientId", {
      value: userConstruct.oidcClientId,
    });
    // new CfnOutput(this, "InitialPassword", {
    //   value: userConstruct.oidcClientId,
    // });
    new CfnOutput(this, "UserPoolId", {
      value: userConstruct.userPool.userPoolId,
    });
  }

  private setBuildConfig() {
    BuildConfig.DEPLOYMENT_MODE =
      this.node.tryGetContext("DeploymentMode") ?? "ALL";
    BuildConfig.LAYER_PIP_OPTION =
      this.node.tryGetContext("LayerPipOption") ?? "";
    BuildConfig.JOB_PIP_OPTION = this.node.tryGetContext("JobPipOption") ?? "";
  }
}

const config = getConfig();

// For development, use account/region from CDK CLI
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();
const stackName = `${config.prefix}intelli-agent`;
new RootStack(app, stackName, { config, env: devEnv });

app.synth();
