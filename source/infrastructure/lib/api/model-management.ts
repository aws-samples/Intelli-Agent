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
import { IAMHelper } from "../shared/iam-helper";


export interface ModelApiProps {
  api: apigw.RestApi;
  auth: apigw.RequestAuthorizer;
  modelTable: string;
  // sharedLayer: pyLambda.PythonLayerVersion;
  iamHelper: IAMHelper;
  genMethodOption: any;
}

export class ModelApi extends Construct {
  private readonly api: apigw.RestApi;
  private readonly auth: apigw.RequestAuthorizer;
  // private readonly sharedLayer: pyLambda.PythonLayerVersion;
  private readonly modelTable: string;
  private readonly iamHelper: IAMHelper;
  private readonly genMethodOption: any;

  constructor(scope: Construct, id: string, props: ModelApiProps) {
    super(scope, id);

    this.api = props.api;
    this.auth = props.auth;
    this.modelTable = props.modelTable;
    // this.sharedLayer = props.sharedLayer;
    this.iamHelper = props.iamHelper;
    this.genMethodOption = props.genMethodOption;

    const modelLambda = new PythonFunction(this, "ModelLambda", {
      runtime: Runtime.PYTHON_3_12,
      memorySize: 512,
      entry: join(__dirname, "../../../lambda/model_management"),
      index: "model_management.py",
      handler: "lambda_handler",
      timeout: Duration.minutes(15),
      environment: {
        MODEL_TABLE_NAME: this.modelTable,
      },
      // layers: [this.sharedLayer],
    });
    modelLambda.addToRolePolicy(this.iamHelper.dynamodbStatement);
    modelLambda.addToRolePolicy(this.iamHelper.logStatement);
    modelLambda.addToRolePolicy(this.iamHelper.s3Statement);
    modelLambda.addToRolePolicy(this.iamHelper.codePipelineStatement);
    modelLambda.addToRolePolicy(this.iamHelper.cfnStatement);
    modelLambda.addToRolePolicy(this.iamHelper.stsStatement);
    modelLambda.addToRolePolicy(this.iamHelper.cfnStatement);
    modelLambda.addToRolePolicy(this.iamHelper.serviceQuotaStatement);
    modelLambda.addToRolePolicy(this.iamHelper.sagemakerModelManagementStatement);

    // API Gateway Lambda Integration to manage model
    const lambdaModelIntegration = new apigw.LambdaIntegration(modelLambda, {
      proxy: true,
    });
    const apiResourceModelManagement = this.api.root.addResource("model-management");
    const apiResourceModelManagementDeploy = apiResourceModelManagement.addResource("deploy")
    apiResourceModelManagementDeploy.addMethod("POST", lambdaModelIntegration, this.genMethodOption(this.api, this.auth, null));
    const apiResourceModelManagementDestroy = apiResourceModelManagement.addResource("destroy")
    apiResourceModelManagementDestroy.addMethod("POST", lambdaModelIntegration, this.genMethodOption(this.api, this.auth, null));
    const apiResourceModelManagementStatus = apiResourceModelManagement.addResource("status").addResource("{modelId}");
    apiResourceModelManagementStatus.addMethod("GET", lambdaModelIntegration, this.genMethodOption(this.api, this.auth, null));
    const apiResourceModelManagementEndpoints = apiResourceModelManagement.addResource("endpoints");
    apiResourceModelManagementEndpoints.addMethod("GET", lambdaModelIntegration, this.genMethodOption(this.api, this.auth, null));
  }
}
