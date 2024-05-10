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
import { BuildConfig } from "./build-config";
import * as pyLambda from "@aws-cdk/aws-lambda-python-alpha";

export class LambdaLayers {
  constructor(private scope: Construct) {}

  createEmbeddingLayer() {
    const LambdaEmbeddingLayer = new LayerVersion(
      this.scope,
      "APILambdaEmbeddingLayer",
      {
        code: Code.fromAsset(
          path.join(__dirname, "../../../lambda/embedding"),
          {
            bundling: {
              image: Runtime.PYTHON_3_11.bundlingImage,
              command: [
                "bash",
                "-c",
                `pip install -r requirements.txt ${BuildConfig.LAYER_PIP_OPTION} -t /asset-output/python`,
              ],
            },
          },
        ),
        compatibleRuntimes: [Runtime.PYTHON_3_11],
        description: `LLM Bot - API layer`,
      },
    );
    return LambdaEmbeddingLayer;
  }

  createOnlineUtilsLayer() {
    const LambdaOnlineUtilsLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "APILambdaOnlineUtilsLayer",
      {
        entry: path.join(__dirname, "../../../lambda/online/layer_logic"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `LLM Bot - Online Utils layer`,
      },
    );
    return LambdaOnlineUtilsLayer;
  }

  createOnlineSourceLayer() {
    const LambdaOnlineSourceLayer = new pyLambda.PythonLayerVersion(
      this.scope,
      "APILambdaOnlineSourceLayer",
      {
        entry: path.join(__dirname, "../../../lambda/online"),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        description: `LLM Bot - Online Source layer`,
      },
    );
    return LambdaOnlineSourceLayer;
  }
}
