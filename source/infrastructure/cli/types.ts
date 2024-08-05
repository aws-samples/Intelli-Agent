
export type ModelProvider = "sagemaker" | "bedrock" | "openai";

export interface SystemConfig {
  prefix: string;
  knowledgeBase: {
    enabled: boolean;
    knowledgeBaseType: {
      intelliAgentKb: {
        enabled: boolean;
        vectorStore: {
          opensearch: {
            enabled: boolean;
          };
        };
        knowledgeBaseModel: {
          enabled: boolean;
          ecrRepository: string;
          ecrImageTag: string;
        };
      };
    };
  };
  chat: {
    enabled: boolean;
  };
  model: {
    embeddingsModels: {
      provider: ModelProvider;
      name: string;
      dimensions: number;
      default?: boolean;
    }[];
    llms: {
      provider: ModelProvider;
      name: string;
    }[];
    modelConfig: {
      modelAssetsBucket: string;
    };
  }
  ui: {
    enabled: boolean;
  };
  federatedAuth: {
    enabled: boolean;
    provider: {
      cognito: {
        enabled: boolean;
      };
      authing: {
        enabled: boolean;
      };
    }
  };
}