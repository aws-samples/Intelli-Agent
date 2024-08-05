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
    prefix: "",
    knowledgeBase: {
      enabled: true,
      knowledgeBaseType: {
        intelliAgentKb: {
          enabled: true,
          vectorStore: {
            opensearch: {
              enabled: true,
            },
          },
          knowledgeBaseModel: {
            enabled: true,
            ecrRepository: "intelli-agent-knowledge-base",
            ecrImageTag: "latest",
          },
        },
      },
    },
    chat: {
      enabled: true,
    },
    model: {
      embeddingsModels: [
        {
          provider: "sagemaker",
          name: "maidalun1020/bce-embedding-base_v1",
          dimensions: 1024,
          default: true,
        },
      ],
      llms: [
        {
          provider: "bedrock",
          name: "anthropic.claude-3-sonnet-20240229-v1:0",
        },
      ],
      modelConfig: {
        modelAssetsBucket: custom_assets_bucket,
      },
    },
    ui: {
      enabled: true,
    },
    federatedAuth: {
      enabled: true,
      provider: {
        cognito: {
          enabled: true,
        },
        authing: {
          enabled: false,
        },
      },
    },
  };
}

export const config: SystemConfig = getConfig();