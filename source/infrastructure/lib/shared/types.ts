
export type ModelProvider = "SageMaker" | "Bedrock" | "OpenAI API";

export interface SystemConfig {
  prefix: string;
  email: string;
  deployRegion: string;
  knowledgeBase: {
    enabled: boolean;
    knowledgeBaseType: {
      intelliAgentKb: {
        enabled: boolean;
        vectorStore: {
          opensearch: {
            enabled: boolean;
            useCustomDomain: boolean;
            customDomainEndpoint: string;
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
    bedrockRegion: string;
    bedrockAk?: string;
    bedrockSk?: string;
    useOpenSourceLLM: boolean;
    amazonConnect: {
      enabled: boolean;
    }
  };
  model: {
    embeddingsModels: {
      provider: ModelProvider;
      id: string;
      commitId: string;
      dimensions: number;
      modelEndpoint?: string;
      default?: boolean;
    }[];
    rerankModels: {
      provider: ModelProvider;
      id: string;
      modelEndpoint?: string;
    }[];
    llms: {
      provider: ModelProvider;
      id: string;
    }[];
    vlms: {
      provider: ModelProvider;
      id: string;
      modelEndpoint?: string;
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
      // authing: {
      //   enabled: boolean;
      // };
    }
  };
}

export enum SupportedRegion {
  AF_SOUTH_1 = "af-south-1",
  AP_EAST_1 = "ap-east-1",
  AP_NORTHEAST_1 = "ap-northeast-1",
  AP_NORTHEAST_2 = "ap-northeast-2",
  AP_NORTHEAST_3 = "ap-northeast-3",
  AP_SOUTH_1 = "ap-south-1",
  AP_SOUTH_2 = "ap-south-2",
  AP_SOUTHEAST_1 = "ap-southeast-1",
  AP_SOUTHEAST_2 = "ap-southeast-2",
  AP_SOUTHEAST_3 = "ap-southeast-3",
  AP_SOUTHEAST_4 = "ap-southeast-4",
  CA_CENTRAL_1 = "ca-central-1",
  EU_CENTRAL_1 = "eu-central-1",
  EU_CENTRAL_2 = "eu-central-2",
  EU_NORTH_1 = "eu-north-1",
  EU_SOUTH_1 = "eu-south-1",
  EU_SOUTH_2 = "eu-south-2",
  EU_WEST_1 = "eu-west-1",
  EU_WEST_2 = "eu-west-2",
  EU_WEST_3 = "eu-west-3",
  IL_CENTRAL_1 = "il-central-1",
  ME_CENTRAL_1 = "me-central-1",
  ME_SOUTH_1 = "me-south-1",
  SA_EAST_1 = "sa-east-1",
  US_EAST_1 = "us-east-1",
  US_EAST_2 = "us-east-2",
  US_WEST_1 = "us-west-1",
  US_WEST_2 = "us-west-2",
  CN_NORTH_1 = "cn-north-1",
  CN_NORTHWEST_1 = "cn-northwest-1",
}

export enum SupportedBedrockRegion {
  US_EAST_1 = "us-east-1",
  US_WEST_2 = "us-west-2",
  AP_NORTHEAST_1 = "ap-northeast-1",
  AP_SOUTHEAST_1 = "ap-southeast-1",
  AP_SOUTHEAST_2 = "ap-southeast-2",
  EU_CENTRAL_1 = "eu-central-1",
  EU_WEST_3 = "eu-west-3",
}