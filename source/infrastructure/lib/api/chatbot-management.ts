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

import { Code, Runtime } from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";
import { join } from "path";
import { LambdaFunction } from "../shared/lambda-helper";
import * as pyLambda from "@aws-cdk/aws-lambda-python-alpha";
import { IAMHelper } from "../shared/iam-helper";
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Provider } from "aws-cdk-lib/custom-resources";
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { CustomResource } from "aws-cdk-lib";
import { SystemConfig } from "../shared/types";

export interface ChatbotManagementApiProps {
    api: apigw.RestApi;
    auth: apigw.RequestAuthorizer;
    indexTableName: string;
    config: SystemConfig;
    chatbotTableName: string;
    modelTableName: string;
    defaultEmbeddingModelName: string;
    sharedLayer: pyLambda.PythonLayerVersion;
    iamHelper: IAMHelper;
    genMethodOption: any;
}

export class ChatbotManagementApi extends Construct {
    constructor(scope: Construct, id: string, props: ChatbotManagementApiProps) {
        super(scope, id);

        // Create Lambda function first
        const chatbotManagementLambda = new LambdaFunction(this, "ChatbotManagementLambda", {
            runtime: Runtime.PYTHON_3_12,
            code: Code.fromAsset(join(__dirname, "../../../lambda/etl")),
            handler: "chatbot_management.lambda_handler",
            environment: {
                INDEX_TABLE_NAME: props.indexTableName,
                CHATBOT_TABLE_NAME: props.chatbotTableName,
                MODEL_TABLE_NAME: props.modelTableName,
                EMBEDDING_ENDPOINT: props.defaultEmbeddingModelName,
            },
            layers: [props.sharedLayer],
            statements: [props.iamHelper.dynamodbStatement,
            props.iamHelper.logStatement],
        });

        // Create Lambda integration once
        const lambdaIntegration = new apigw.LambdaIntegration(chatbotManagementLambda.function, {
            proxy: true,
        });

        // Create all resources first
        const apiResourceChatbotManagement = props.api.root.addResource("chatbot-management");
        const apiResourceCheckDefaultChatbot = apiResourceChatbotManagement.addResource('default-chatbot');
        const apiResourceCheckChatbot = apiResourceChatbotManagement.addResource('check-chatbot');
        const apiResourceCheckIndex = apiResourceChatbotManagement.addResource('check-index');
        const apiResourceListIndex = apiResourceChatbotManagement.addResource('indexes').addResource('{chatbotId}');
        const apiResourceEditChatBot = apiResourceChatbotManagement.addResource('edit-chatbot');
        const apiResourceChatbots = apiResourceChatbotManagement.addResource("chatbots");
        const apiResourceChatbotProxy = apiResourceChatbots.addResource("{proxy+}");
        const apiResourceEmbeddings = apiResourceChatbotManagement.addResource("embeddings");

        // Add methods with their correct HTTP verbs and schemas
        apiResourceCheckDefaultChatbot.addMethod(
            "GET",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceCheckChatbot.addMethod(
            "POST",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceCheckIndex.addMethod(
            "POST",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceListIndex.addMethod(
            "GET",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceEditChatBot.addMethod(
            "POST",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceChatbots.addMethod(
            "GET",
            lambdaIntegration,
            {
                ...props.genMethodOption(props.api, props.auth, null),
                requestParameters: {
                    'method.request.querystring.max_items': false,
                    'method.request.querystring.page_size': false
                }
            }
        );

        apiResourceChatbots.addMethod(
            "POST",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceChatbotProxy.addMethod(
            "GET",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceChatbotProxy.addMethod(
            "DELETE",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        apiResourceEmbeddings.addMethod(
            "GET",
            lambdaIntegration,
            props.genMethodOption(props.api, props.auth, null)
        );

        const provider = this.createInitChatbotProvider(props);

        new CustomResource(this, `InitChatbot${id}`, {
            serviceToken: provider.serviceToken
        });
    };

    private initChatbotProvider!: Provider;
    private createInitChatbotProvider(props: ChatbotManagementApiProps) {
        if (!this.initChatbotProvider) {
          // Create a Lambda function that implements the delay logic
          const chatbotInitFunction = new lambda.Function(this, "ChatbotInitLambda", {
            runtime: Runtime.PYTHON_3_12,
            code: Code.fromAsset(join(__dirname, "../../../lambda/init_chatbot")),
            handler: "main.handler",
            environment: {
                MODEL_TABLE_NAME: props.modelTableName,
                CHATBOT_TABLE_NAME: props.chatbotTableName,
                INDEX_TABLE_NAME: props.indexTableName,
                MODEL_INFO: JSON.stringify(props.config.model)
            },
            layers: [props.sharedLayer]
        });
        dynamodb.Table.fromTableName(this, 'modelTable',  props.modelTableName).grantWriteData(chatbotInitFunction);
        dynamodb.Table.fromTableName(this, 'chatbotTable',  props.chatbotTableName).grantWriteData(chatbotInitFunction);
        dynamodb.Table.fromTableName(this, 'indexTable',  props.indexTableName).grantWriteData(chatbotInitFunction);

          // Create the provider that will handle the custom resource
          this.initChatbotProvider = new Provider(this, 'InitChatbotProvider', {
            onEventHandler: chatbotInitFunction,
          });
        }
        return this.initChatbotProvider;
    }
    
} 