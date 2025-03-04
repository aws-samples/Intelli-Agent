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
import { getConfig } from "./config";
import { SystemConfig } from "../lib/shared/types";
import { SharedConstruct, SharedConstructOutputs } from "../lib/shared/shared-construct";
import { ApiConstruct, ApiConstructOutputs } from "../lib/api/api-stack";
import { ModelConstruct, ModelConstructOutputs } from "../lib/model/model-construct";
import { KnowledgeBaseStack, KnowledgeBaseStackOutputs } from "../lib/knowledge-base/knowledge-base-stack";
import { ChatStack, ChatStackOutputs } from "../lib/chat/chat-stack";
import { WorkspaceStack } from "../lib/workspace/workspace-stack";
import { UIStack } from "../lib/ui/ui-stack";
import { Fn } from "aws-cdk-lib";

dotenv.config();

export interface RootStackProps extends StackProps {
  readonly config: SystemConfig;
  readonly portalBucketName: string;
  readonly portalUrl: string;
}

export class RootStack extends Stack {
  public sharedConstruct: SharedConstructOutputs;
  public apiConstruct: ApiConstructOutputs;
  public modelConstruct: ModelConstructOutputs;
  public config: SystemConfig;

  constructor(scope: Construct, id: string, props: RootStackProps) {
    super(scope, id, props);
    this.templateOptions.description = "(SO8034) - Intelli-Agent";

    const sharedConstruct = new SharedConstruct(this, "shared-construct", {
      config: props.config,
    });

    let knowledgeBaseStack: KnowledgeBaseStack = {} as KnowledgeBaseStack;
    let knowledgeBaseStackOutputs: KnowledgeBaseStackOutputs = {} as KnowledgeBaseStackOutputs;
    let chatStackOutputs: ChatStackOutputs = {} as ChatStackOutputs;

    const modelConstruct = new ModelConstruct(this, "model-construct", {
      config: props.config,
      sharedConstructOutputs: sharedConstruct,
    });
    modelConstruct.node.addDependency(sharedConstruct);

    if (props.config.knowledgeBase.enabled && props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled) {
      knowledgeBaseStack = new KnowledgeBaseStack(this, "knowledge-base-stack", {
        config: props.config,
        sharedConstructOutputs: sharedConstruct,
        modelConstructOutputs: modelConstruct,
        uiPortalBucketName: props.portalBucketName,
      });
      knowledgeBaseStack.node.addDependency(sharedConstruct);
      knowledgeBaseStack.node.addDependency(modelConstruct);
      knowledgeBaseStackOutputs = knowledgeBaseStack;
    }

    if (props.config.chat.enabled) {
      const chatStack = new ChatStack(this, "chat-stack", {
        config: props.config,
        sharedConstructOutputs: sharedConstruct,
        modelConstructOutputs: modelConstruct,
        domainEndpoint: knowledgeBaseStackOutputs.aosDomainEndpoint,
      });
      chatStackOutputs = chatStack;
    }
    
    const apiConstruct = new ApiConstruct(this, "api-construct", {
      config: props.config,
      sharedConstructOutputs: sharedConstruct,
      modelConstructOutputs: modelConstruct,
      knowledgeBaseStackOutputs: knowledgeBaseStackOutputs,
      chatStackOutputs: chatStackOutputs
    });
    apiConstruct.node.addDependency(sharedConstruct);
    apiConstruct.node.addDependency(modelConstruct);

    this.sharedConstruct = sharedConstruct;
    this.apiConstruct = apiConstruct;
    this.modelConstruct = modelConstruct;
    this.config = props.config;

    new CfnOutput(this, "API Endpoint Address", {
      value: apiConstruct.apiEndpoint,
    });
    new CfnOutput(this, "Web Portal URL", {
      value: props.portalUrl,
      description: "Web portal url",
    });
    new CfnOutput(this, "WebSocket Endpoint Address", {
      value: apiConstruct.wsEndpoint,
    });
  }
}


const config = getConfig();

// For development, use account/region from CDK CLI
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
  region: process.env.CDK_DEFAULT_REGION || process.env.AWS_REGION || "us-east-1",
};

const app = new App();
let stackName = "ai-customer-service"
if(config.prefix && config.prefix.trim().length > 0){
  stackName = `${config.prefix}-ai-customer-service`;
}

const uiStack = new UIStack(app, `${stackName}-frontend`, {
  config: config,
  env: devEnv,
  suppressTemplateIndentation: true,
});

const rootStack = new RootStack(app, stackName, {
  config,
  env: devEnv,
  portalBucketName: Fn.importValue(`${stackName}-frontend-portal-bucket-name`),
  portalUrl: Fn.importValue(`${stackName}-frontend-portal-url`),
  suppressTemplateIndentation: true,
});

const workspaceStack = new WorkspaceStack(app, `${stackName}-workspace`, {
  env: devEnv,
  config: config,
  sharedConstructOutputs: rootStack.sharedConstruct,
  apiConstructOutputs: rootStack.apiConstruct,
  modelConstructOutputs: rootStack.modelConstruct,
  portalBucketName: Fn.importValue(`${stackName}-frontend-portal-bucket-name`),
  clientPortalBucketName: Fn.importValue(`${stackName}-frontend-client-portal-bucket-name`),
  portalUrl: Fn.importValue(`${stackName}-frontend-portal-url`),
  clientPortalUrl: Fn.importValue(`${stackName}-frontend-client-portal-url`),
  suppressTemplateIndentation: true,
  userPoolId: Fn.importValue(`${stackName}-frontend-user-pool-id`),
  oidcClientId: Fn.importValue(`${stackName}-frontend-oidc-client-id`),
  oidcIssuer: Fn.importValue(`${stackName}-frontend-oidc-issuer`),
  oidcLogoutUrl: Fn.importValue(`${stackName}-frontend-oidc-logout-url`),
  oidcRegion: Fn.importValue(`${stackName}-frontend-oidc-region`),
  oidcDomain: Fn.importValue(`${stackName}-frontend-oidc-domain`)
  // oidcScopes: config.auth.oidcScopes,
  // oidcResponseType: config.auth.oidcResponseType
});
// Add dependencies
rootStack.addDependency(uiStack);
workspaceStack.addDependency(rootStack);
workspaceStack.addDependency(uiStack);

app.synth();
