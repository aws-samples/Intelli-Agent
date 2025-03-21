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

import { Duration } from "aws-cdk-lib";
import { Runtime } from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";
import { join } from "path";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as pyLambda from "@aws-cdk/aws-lambda-python-alpha";
import { IAMHelper } from "../shared/iam-helper";
import { Vpc, SecurityGroup } from 'aws-cdk-lib/aws-ec2';
import { SystemConfig } from "../shared/types";


export interface IntentionApiProps {
  api: apigw.RestApi;
  auth: apigw.RequestAuthorizer;
  vpc: Vpc;
  securityGroups: [SecurityGroup];
  intentionTableName: string;
  indexTable: string;
  chatbotTable: string;
  modelTable: string;
  s3Bucket: string;
  defaultEmbeddingModelName: string;
  domainEndpoint: string;
  config: SystemConfig;
  sharedLayer: pyLambda.PythonLayerVersion;
  iamHelper: IAMHelper;
  genMethodOption: any;
}

export class IntentionApi extends Construct {
  private readonly api: apigw.RestApi;
  private readonly auth: apigw.RequestAuthorizer;
  private readonly vpc: Vpc;
  private readonly securityGroups: [SecurityGroup];
  private readonly sharedLayer: pyLambda.PythonLayerVersion;
  private readonly iamHelper: IAMHelper;
  private readonly intentionTableName: string;
  private readonly indexTable: string;
  private readonly chatbotTable: string;
  private readonly modelTable: string;
  private readonly s3Bucket: string;
  private readonly defaultEmbeddingModelName: string;
  private readonly domainEndpoint: string;
  private readonly config: SystemConfig;
  private readonly genMethodOption: any;

  constructor(scope: Construct, id: string, props: IntentionApiProps) {
    super(scope, id);
    
    this.api = props.api;
    this.auth = props.auth;
    this.vpc = props.vpc;
    this.securityGroups = props.securityGroups;
    this.intentionTableName = props.intentionTableName;
    this.indexTable = props.indexTable;
    this.chatbotTable = props.chatbotTable;
    this.modelTable = props.modelTable;
    this.s3Bucket = props.s3Bucket;
    this.defaultEmbeddingModelName = props.defaultEmbeddingModelName;
    this.domainEndpoint = props.domainEndpoint;
    this.config = props.config;
    this.sharedLayer = props.sharedLayer;
    this.iamHelper = props.iamHelper;
    this.genMethodOption = props.genMethodOption;

    const intentionLambda = new PythonFunction(scope, "IntentionLambda", {
      runtime: Runtime.PYTHON_3_12,
      entry: join(__dirname, "../../../lambda/intention"),
      index: "intention.py",
      memorySize: 1024,
      handler: "lambda_handler",
      timeout: Duration.minutes(15),
      vpc: this.vpc,
      securityGroups: this.securityGroups,
      environment: {
        INTENTION_TABLE_NAME: this.intentionTableName,
        INDEX_TABLE_NAME: this.indexTable,
        CHATBOT_TABLE_NAME: this.chatbotTable,
        MODEL_TABLE_NAME: this.modelTable,
        S3_BUCKET: this.s3Bucket,
        EMBEDDING_MODEL_ENDPOINT: this.defaultEmbeddingModelName,
        AOS_ENDPOINT: this.domainEndpoint,
        KNOWLEDGE_BASE_ENABLED: this.config.knowledgeBase.enabled.toString(),
        KNOWLEDGE_BASE_TYPE: JSON.stringify(this.config.knowledgeBase.knowledgeBaseType || {}),
        BEDROCK_REGION: this.config.chat.bedrockRegion,
      },
      layers: [this.sharedLayer],
    });
    intentionLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);
    intentionLambda.addToRolePolicy(this.iamHelper.logStatement);
    intentionLambda.addToRolePolicy(this.iamHelper.secretStatement);
    intentionLambda.addToRolePolicy(this.iamHelper.esStatement);
    intentionLambda.addToRolePolicy(this.iamHelper.s3Statement);
    intentionLambda.addToRolePolicy(this.iamHelper.bedrockStatement);
    intentionLambda.addToRolePolicy(this.iamHelper.endpointStatement);

    // API Gateway Lambda Integration to manage intention
    const lambdaIntentionIntegration = new apigw.LambdaIntegration(intentionLambda, {
      proxy: true,
    });
    const apiResourceIntentionManagement = this.api.root.addResource("intention");
    const indexScan = apiResourceIntentionManagement.addResource("index-used-scan")
    indexScan.addMethod("POST", lambdaIntentionIntegration, this.genMethodOption(this.api, this.auth, null));
    const presignedUrl = apiResourceIntentionManagement.addResource("execution-presigned-url");
    presignedUrl.addMethod("POST", lambdaIntentionIntegration, this.genMethodOption(this.api, this.auth, null));
    const apiResourceDownload = apiResourceIntentionManagement.addResource("download-template");
    apiResourceDownload.addMethod("GET", lambdaIntentionIntegration, this.genMethodOption(this.api, this.auth, null));

    const apiResourceIntentionExecution = apiResourceIntentionManagement.addResource("executions");
    apiResourceIntentionExecution.addMethod("DELETE", lambdaIntentionIntegration, this.genMethodOption(this.api, this.auth, null));
    apiResourceIntentionExecution.addMethod("POST", lambdaIntentionIntegration, this.genMethodOption(this.api, this.auth, null));
    apiResourceIntentionExecution.addMethod("GET", lambdaIntentionIntegration, {
      ...this.genMethodOption(this.api, this.auth, null),
      requestParameters: {
        'method.request.querystring.max_items': false,
        'method.request.querystring.page_size': false
      }
    });
    const apiGetIntentionById = apiResourceIntentionExecution.addResource("{executionId}");
    apiGetIntentionById.addMethod(
      "GET",
      lambdaIntentionIntegration,
      {
        ...this.genMethodOption(this.api, this.auth, null),
        requestParameters: {
          'method.request.path.intentionId': true
        },
      }
    );
  }
}
