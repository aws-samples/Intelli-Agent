import { SystemConfig } from "../lib/shared/types";
import { existsSync, readFileSync } from "fs";

export function getConfig(): SystemConfig {
  if (existsSync("./bin/config.json")) {
    return JSON.parse(readFileSync("./bin/config.json").toString("utf8"));
  }
  let AWS_ACCOUNT = process.env.CDK_DEFAULT_ACCOUNT;
  let AWS_REGION = process.env.CDK_DEFAULT_REGION;
  let custom_assets_bucket = "intelli-agent-model" + AWS_ACCOUNT + "-" + AWS_REGION;
  // Default config
  return {
    prefix: "",
    email: "support@example.com",
    deployRegion: "us-east-1",
    knowledgeBase: {
      enabled: true,
      knowledgeBaseType: {
        intelliAgentKb: {
          enabled: true,
          vectorStore: {
            opensearch: {
              enabled: true,
              useCustomDomain: false,
              customDomainEndpoint: ""
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
      bedrockRegion: "us-east-1",
      bedrockAk: "",
      bedrockSk: "",
      useOpenSourceLLM: true,
      amazonConnect: {
        enabled: true
      }
    },
    model: {
      embeddingsModels: [
        {
          provider: "Bedrock",
          id: "amazon.titan-embed-text-v2",
          commitId: "",
          dimensions: 1024,
          default: true
        }
      ],
      rerankModels: [
        {
          provider: "Bedrock",
          id: "bge-reranker-v2-m3",
        },
      ],
      llms: [
        {
          provider: "Bedrock",
          id: "anthropic.claude-3-sonnet-20240229-v1:0",
        },
      ],
      vlms: [
        {
          provider: "Bedrock",
          id: "amazon.titan-embed-text-v2",
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
        // authing: {
        //   enabled: false,
        // },
      },
    },
  };
}

export const config: SystemConfig = getConfig();
