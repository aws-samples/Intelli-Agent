import { LayerVersion, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import { Construct } from "constructs";
import { BuildConfig } from "./build-config";

export class LambdaLayers {
  constructor(private scope: Construct) {}

  createEmbeddingLayer() {
    const LambdaEmbeddingLayer = new LayerVersion(this.scope, "APILambdaEmbeddingLayer", {
      code: Code.fromAsset(path.join(__dirname, "../../../lambda/embedding"), {
        bundling: {
          image: Runtime.PYTHON_3_11.bundlingImage,
          command: [
            "bash",
            "-c",
            `pip install -r requirements.txt ${BuildConfig.LAYER_PIP_OPTION} -t /asset-output/python`,
          ],
        },
      }),
      compatibleRuntimes: [Runtime.PYTHON_3_11],
      description: `LLM Bot - API layer`,
    });
    return LambdaEmbeddingLayer;
  }
}