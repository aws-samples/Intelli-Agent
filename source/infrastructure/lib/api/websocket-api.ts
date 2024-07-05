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

interface WebSocketProps extends StackProps {
  dispatcherLambda: lambda.Function;
  sendMessageLambda: lambda.Function;
  customAuthorizerLambda: lambda.Function;
}

export class WebSocketConstruct extends Construct {
  public readonly webSocketApi: apigwv2.WebSocketApi;
  public readonly websocketApiStage: apigwv2.WebSocketStage;

  constructor(scope: Construct, id: string, props: WebSocketProps) {
    super(scope, id);
    const lambdaRole = new iam.Role(this, "wsLambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      inlinePolicies: {
        LambdaFunctionServiceRolePolicy: createBasicLambdaPolicy(),
      },
    });

    const onConnectLambda = new lambda.Function(this, "OnConnect", {
      code: lambda.Code.fromAsset(
        join(__dirname, "../../../lambda/websocket/connect"),
      ),
      role: lambdaRole,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "connect.lambda_handler",
      timeout: Duration.minutes(15),
    });

    const onDisconnectLambda = new lambda.Function(this, "OnDisconnect", {
      code: lambda.Code.fromAsset(
        join(__dirname, "../../../lambda/websocket/disconnect"),
      ),
      role: lambdaRole,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "disconnect.lambda_handler",
      timeout: Duration.minutes(15),
    });

    const webSocketApi = new apigwv2.WebSocketApi(this, "wsApi", {
      description: "LLM bot WebSocket API",
      connectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          "ConnectIntegration",
          onConnectLambda,
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
          onDisconnectLambda,
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
