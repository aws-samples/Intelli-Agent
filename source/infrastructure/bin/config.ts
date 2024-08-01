import { SystemConfig } from "../cli/types";
import { existsSync, readFileSync } from "fs";

export function getConfig(): SystemConfig {
  let AWS_ACCOUNT = process.env.CDK_DEFAULT_ACCOUNT;
  let AWS_REGION = process.env.CDK_DEFAULT_REGION;
  let custom_assets_bucket = "intelli-agent-model" + AWS_ACCOUNT + "-" + AWS_REGION;
  if (existsSync("./bin/config.json")) {
    return JSON.parse(readFileSync("./bin/config.json").toString("utf8"));
  }
  // Default config
  return {
    knowledgeBase: {
      enabled: true,
      knowledgeBaseModels: {
        enabled: true,
        ecrRepository: "intelli-agent-knowledge-base",
        ecrImageTag: "latest",
      },
    },
    llms: {},
    rag: {
      enabled: true,
      engines: {
        opensearch: {
          enabled: true,
        },
        smartsearch: {
          enabled: false,
        },
      },
      embeddingsModels: [
        "maidalun1020/bce-embedding-base_v1"
      ],
      crossEncoderModels: [
      ],
    },
    sagemaker: {
      modelAssetsBucket: custom_assets_bucket,
    },
    ui: {
      enabled: true,
    },
  };
}

export const config: SystemConfig = getConfig();