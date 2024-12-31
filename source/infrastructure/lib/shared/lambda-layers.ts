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

import { LayerVersion, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import { Construct } from "constructs";
import * as pyLambda from "@aws-cdk/aws-lambda-python-alpha";

export class LambdaLayers {
  constructor(private scope: Construct) { }

  createSharedLayer() {
    const sharedLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "AICSSharedLayer",
      {
        entry: path.join(__dirname, "../../../lambda/online"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `AI-Customer-Service - Online Source layer`,
        bundling: {
          "command": [
            "bash", "-c", "pip install -r requirements.txt -t /asset-output/python"],
          "assetExcludes": [
            "*.pyc", "*/__pycache__/*",
            "*.xls", "*.xlsx", "*.csv",
            "*.png",
            "*.md",
            "*.zip",
            "lambda_main/retail/size/*"],
        }
      },
    );
    return sharedLayer;
  }

  createModelDeploymentLayer() {
    const modelDeploymentLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "AICSModelDeploymentLayer",
      {
        entry: path.join(__dirname, "../../../lambda/model_management"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `AI Customer Service - Model deployment layer`,
        bundling: {
          "command": [
            "bash", "-c", "pip install -r requirements.txt -t /asset-output/python"],
          "assetExcludes": [
            "*.pyc", "*/__pycache__/*",
            "*.xls", "*.xlsx", "*.csv",
            "*.png",
            "*.md",
            "*.zip"]
        }
      },
    );
    return modelDeploymentLayer;
  }

  createJobSourceLayer() {
    const etlLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "AICSETLLayer",
      {
        entry: path.join(__dirname, "../../../lambda/job/dep/llm_bot_dep"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `AI Customer Service - Job Source layer`,
      },
    );
    return etlLayer;
  }

  createAuthorizerLayer() {
    const authorizerLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "AICSAuthorizerLayer",
      {
        entry: path.join(__dirname, "../../../lambda/authorizer"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `LLM Bot - Authorizer layer`,
      },
    );
    return authorizerLayer;
  }
}
