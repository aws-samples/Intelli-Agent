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
import { SystemConfig } from "../lib/shared/types";
import { SharedConstruct } from "../lib/shared/shared-construct";
import { ApiConstruct } from "../lib/api/api-stack";
import { ModelConstruct } from "../lib/model/model-construct";
import { KnowledgeBaseStack, KnowledgeBaseStackOutputs } from "../lib/knowledge-base/knowledge-base-stack";
import { PortalConstruct } from "../lib/ui/ui-portal";
import { UiExportsConstruct } from "../lib/ui/ui-exports";
import { UserConstruct } from "../lib/user/user-construct";
import { ChatStack, ChatStackOutputs } from "../lib/chat/chat-stack";

dotenv.config();

export interface RootStackProps extends StackProps {
  readonly config: SystemConfig;
}

export class RootStack extends Stack {
  constructor(scope: Construct, id: string, props: RootStackProps) {
    super(scope, id, props);
    this.templateOptions.description = "(SO8034) - Intelli-Agent";

    let knowledgeBaseStack: KnowledgeBaseStack = {} as KnowledgeBaseStack;
    let knowledgeBaseStackOutputs: KnowledgeBaseStackOutputs = {} as KnowledgeBaseStackOutputs;
    let chatStack: ChatStack = {} as ChatStack;
    let chatStackOutputs: ChatStackOutputs = {} as ChatStackOutputs;

    const sharedConstruct = new SharedConstruct(this, "shared-construct", {
      config: props.config,
    });

    const modelConstruct = new ModelConstruct(this, "model-construct", {
      config: props.config,
      sharedConstructOutputs: sharedConstruct,
    });
    modelConstruct.node.addDependency(sharedConstruct);

    const portalConstruct = new PortalConstruct(this, "ui-construct");

    if (props.config.knowledgeBase.enabled && props.config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled) {
      knowledgeBaseStack = new KnowledgeBaseStack(this, "knowledge-base-stack", {
        config: props.config,
        sharedConstructOutputs: sharedConstruct,
        modelConstructOutputs: modelConstruct,
        uiPortalBucketName: portalConstruct.portalBucket.bucketName,
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
    
    const userConstruct = new UserConstruct(this, "user", {
      adminEmail: props.config.email,
      callbackUrl: portalConstruct.portalUrl,
    });

    const apiConstruct = new ApiConstruct(this, "api-construct", {
      config: props.config,
      sharedConstructOutputs: sharedConstruct,
      modelConstructOutputs: modelConstruct,
      knowledgeBaseStackOutputs: knowledgeBaseStackOutputs,
      chatStackOutputs: chatStackOutputs,
      userConstructOutputs: userConstruct,
    });
    apiConstruct.node.addDependency(sharedConstruct);
    apiConstruct.node.addDependency(modelConstruct);
    apiConstruct.node.addDependency(portalConstruct);
    if (chatStack.node) {
      apiConstruct.node.addDependency(chatStack);
    }
    if (knowledgeBaseStack.node) {
      apiConstruct.node.addDependency(knowledgeBaseStack);
    }

    const uiExports = new UiExportsConstruct(this, "ui-exports", {
      portalBucket: portalConstruct.portalBucket,
      uiProps: {
        websocket: apiConstruct.wsEndpoint,
        apiUrl: apiConstruct.apiEndpoint,
        oidcIssuer: userConstruct.oidcIssuer,
        oidcClientId: userConstruct.oidcClientId,
        oidcLogoutUrl: userConstruct.oidcLogoutUrl,
        region: props.env?.region || "us-east-1",
        oidcRedirectUrl: `https://${portalConstruct.portalUrl}/signin`,
        kbEnabled: props.config.knowledgeBase.enabled.toString(),
        kbType: JSON.stringify(props.config.knowledgeBase.knowledgeBaseType || {}),
        embeddingEndpoint: modelConstruct.defaultEmbeddingModelName || "",
        // apiKey: apiConstruct.apiKey,
      },
    });
    uiExports.node.addDependency(portalConstruct);

    new CfnOutput(this, "API Endpoint Address", {
      value: apiConstruct.apiEndpoint,
    });
    new CfnOutput(this, "Web Portal URL", {
      value: portalConstruct.portalUrl,
      description: "Web portal url",
    });
    new CfnOutput(this, "WebSocket Endpoint Address", {
      value: apiConstruct.wsEndpoint,
    });
    new CfnOutput(this, "OIDC Client ID", {
      value: userConstruct.oidcClientId,
    });
    // new CfnOutput(this, "InitialPassword", {
    //   value: userConstruct.oidcClientId,
    // });
    new CfnOutput(this, "User Pool ID", {
      value: userConstruct.userPool.userPoolId,
    });
  }
}

const config = getConfig();

// For development, use account/region from CDK CLI
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();
const stackName = `${config.prefix}ai-customer-service`;
new RootStack(app, stackName, { config, env: devEnv, suppressTemplateIndentation: true });

app.synth();
