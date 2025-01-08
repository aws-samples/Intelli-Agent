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

import { Code } from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";
import { join } from "path";
import { IAMHelper } from "../shared/iam-helper";
import { LambdaFunction } from "../shared/lambda-helper";


export interface ChatHistoryApiProps {
  api: apigw.RestApi;
  auth: apigw.RequestAuthorizer;
  iamHelper: IAMHelper;
  messagesTableName: string;
  sessionsTableName: string;
  genMethodOption: any;
}

export class ChatHistoryApi extends Construct {
  private readonly api: apigw.RestApi;
  private readonly auth: apigw.RequestAuthorizer;
  private readonly messagesTableName: string;
  private readonly sessionsTableName: string;
  private readonly iamHelper: IAMHelper;
  private readonly genMethodOption: any;

  constructor(scope: Construct, id: string, props: ChatHistoryApiProps) {
    super(scope, id);
    
    this.api = props.api;
    this.auth = props.auth;
    this.messagesTableName = props.messagesTableName;
    this.sessionsTableName = props.sessionsTableName;
    this.iamHelper = props.iamHelper;
    this.genMethodOption = props.genMethodOption;

    const chatHistoryManagementLambda = new LambdaFunction(this, "ChatHistoryManagementLambda", {
      code: Code.fromAsset(join(__dirname, "../../../lambda/chat_history")),
      handler: "chat_history_management.lambda_handler",
      environment: {
        SESSIONS_TABLE_NAME: this.sessionsTableName,
        MESSAGES_TABLE_NAME: this.messagesTableName,
        SESSIONS_BY_TIMESTAMP_INDEX_NAME: "byTimestamp",
        MESSAGES_BY_SESSION_ID_INDEX_NAME: "bySessionId",
      },
      statements: [this.iamHelper.dynamodbStatement],
    });

    const apiResourceSessions = this.api.root.addResource("sessions");
    apiResourceSessions.addMethod("GET", new apigw.LambdaIntegration(chatHistoryManagementLambda.function), this.genMethodOption(this.api, this.auth, null),);
    const apiResourceMessages = apiResourceSessions.addResource('{sessionId}').addResource("messages");
    apiResourceMessages.addMethod("GET", new apigw.LambdaIntegration(chatHistoryManagementLambda.function), this.genMethodOption(this.api, this.auth, null),);
    const apiResourceMessageFeedback = apiResourceMessages.addResource("{messageId}").addResource("feedback");
    apiResourceMessageFeedback.addMethod("POST", new apigw.LambdaIntegration(chatHistoryManagementLambda.function), this.genMethodOption(this.api, this.auth, null),);
  }
}
