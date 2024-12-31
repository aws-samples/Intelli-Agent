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

import { Runtime, Code } from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";
import { join } from "path";
import { LambdaFunction } from "../shared/lambda-helper";
import * as pyLambda from "@aws-cdk/aws-lambda-python-alpha";
import { IAMHelper } from "../shared/iam-helper";


export interface PromptApiProps {
  api: apigw.RestApi;
  auth: apigw.RequestAuthorizer;
  promptTableName: string;
  sharedLayer: pyLambda.PythonLayerVersion;
  iamHelper: IAMHelper;
  genMethodOption: any;
}

export class PromptApi extends Construct {
  private readonly api: apigw.RestApi;
  private readonly auth: apigw.RequestAuthorizer;
  private readonly promptTableName: string;
  private readonly sharedLayer: pyLambda.PythonLayerVersion;
  private readonly iamHelper: IAMHelper;
  private readonly genMethodOption: any;

  constructor(scope: Construct, id: string, props: PromptApiProps) {
    super(scope, id);

    this.api = props.api;
    this.auth = props.auth;
    this.promptTableName = props.promptTableName;
    this.sharedLayer = props.sharedLayer;
    this.iamHelper = props.iamHelper;
    this.genMethodOption = props.genMethodOption;

    const promptManagementLambda = new LambdaFunction(scope, "PromptManagementLambda", {
      runtime: Runtime.PYTHON_3_12,
      handler: "prompt_management.lambda_handler",
      code: Code.fromAsset(join(__dirname, '../../../lambda/deployment_assets/lambda_assets/prompt_management.zip')),
      environment: {
        PROMPT_TABLE_NAME: this.promptTableName,
      },
      layers: [this.sharedLayer],
      statements: [this.iamHelper.dynamodbStatement, this.iamHelper.logStatement],
    });
    // API Gateway Lambda Integration to manage prompt
    const lambdaPromptIntegration = new apigw.LambdaIntegration(promptManagementLambda.function, {
      proxy: true,
    });

    const apiResourcePromptManagement = this.api.root.addResource("prompt-management");

    const apiResourcePromptManagementModels = apiResourcePromptManagement.addResource("models")
    apiResourcePromptManagementModels.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));

    const apiResourcePromptManagementScenes = apiResourcePromptManagement.addResource("scenes")
    apiResourcePromptManagementScenes.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));

    const apiResourcePrompt = apiResourcePromptManagement.addResource("prompts");
    apiResourcePrompt.addMethod("POST", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));
    apiResourcePrompt.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));

    const apiResourcePromptProxy = apiResourcePrompt.addResource("{proxy+}")
    apiResourcePromptProxy.addMethod("POST", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));
    apiResourcePromptProxy.addMethod("DELETE", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));
    apiResourcePromptProxy.addMethod("GET", lambdaPromptIntegration, this.genMethodOption(this.api, this.auth, null));
  }
}
