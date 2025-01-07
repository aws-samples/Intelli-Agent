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

import { Duration, StackProps } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import { Construct } from "constructs";
import { join } from "path";

import { WebSocketLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { WebSocketLambdaAuthorizer } from 'aws-cdk-lib/aws-apigatewayv2-authorizers';

import { createBasicLambdaPolicy } from "../shared/utils";
import { LambdaFunction } from "../shared/lambda-helper";
import { Constants } from "../shared/constants";

interface WSWebSocketProps extends StackProps {
  dispatcherLambda: lambda.Function;
  sendMessageLambda: lambda.Function;
  customAuthorizerLambda: lambda.Function;
  sessionTableName: string;
  messageTableName: string;
  sessionIndex: string;
  messageIndex: string;
}

export class WSWebSocketConstruct extends Construct {
  public readonly webSocketApi: apigwv2.WebSocketApi;
  public readonly websocketApiStage: apigwv2.WebSocketStage;

  constructor(scope: Construct, id: string, props: WSWebSocketProps) {
    super(scope, id);
    const lambdaRole = new iam.Role(this, "wsLambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      inlinePolicies: {
        LambdaFunctionServiceRolePolicy: createBasicLambdaPolicy(),
      },
    });

    const onConnectLambda = new LambdaFunction(this, "OnConnect", {
      code: lambda.Code.fromAsset(
        join(__dirname, "../../../lambda/workspace"),
      ),
      role: lambdaRole,
      handler: "connect.lambda_handler",
      environment: {
        SESSIONS_TABLE_NAME: props.sessionTableName,
        MESSAGES_TABLE_NAME: props.messageTableName,
        SESSIONS_BY_TIMESTAMP_INDEX_NAME: props.sessionIndex,
        MESSAGES_BY_SESSION_ID_INDEX_NAME: props.messageIndex,
      },
    });

    const onDisconnectLambda = new LambdaFunction(this, "OnDisconnect", {
      code: lambda.Code.fromAsset(
        join(__dirname, "../../../lambda/workspace"),
      ),
      role: lambdaRole,
      handler: "disconnect.lambda_handler",
      environment: {
        SESSIONS_TABLE_NAME: props.sessionTableName,
        MESSAGES_TABLE_NAME: props.messageTableName,
        SESSIONS_BY_TIMESTAMP_INDEX_NAME: props.sessionIndex,
        MESSAGES_BY_SESSION_ID_INDEX_NAME: props.messageIndex,
      },
    });

    const webSocketApi = new apigwv2.WebSocketApi(this, `${Constants.SOLUTION_SHORT_NAME.toLowerCase()}-workspace-ws-api`, {
      description: `${Constants.SOLUTION_NAME} - Workspace WebSocket API`,
      connectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          "ConnectIntegration",
          onConnectLambda.function,
        ),
        authorizer: new WebSocketLambdaAuthorizer('Authorizer',
          props.customAuthorizerLambda,
          {
            identitySource: ["route.request.querystring.idToken"],
          })
      },
      disconnectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          "DisconnectIntegration",
          onDisconnectLambda.function,
        ),
      },
      defaultRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          "DefaultRouteIntegration",
          props.dispatcherLambda,
        ),
      },
    });

    const stage = new apigwv2.WebSocketStage(this, "prod", {
      webSocketApi: webSocketApi,
      stageName: "prod",
      autoDeploy: true,
    });

    webSocketApi.addRoute("sendMessage", {
      integration: new WebSocketLambdaIntegration(
        "MessageIntegration",
        props.dispatcherLambda,
      ),
    });

    props.sendMessageLambda.addEnvironment("WEBSOCKET_URL", stage.callbackUrl);
    webSocketApi.grantManageConnections(props.sendMessageLambda);
    webSocketApi.grantManageConnections(props.dispatcherLambda);

    this.webSocketApi = webSocketApi;
    this.websocketApiStage = stage;
  }
}
