import * as sagemaker from "aws-cdk-lib/aws-sagemaker";

export type ModelProvider = "sagemaker" | "bedrock" | "openai";

export enum SupportedSageMakerModels {
  FalconLite = "FalconLite [ml.g5.12xlarge]",
  Llama2_13b_Chat = "Llama2_13b_Chat [ml.g5.12xlarge]",
  Mistral7b_Instruct = "Mistral7b_Instruct 0.1 [ml.g5.2xlarge]",
  Mistral7b_Instruct2 = "Mistral7b_Instruct 0.2 [ml.g5.2xlarge]",
  Mixtral_8x7b_Instruct = "Mixtral_8x7B_Instruct 0.1 [ml.g5.48xlarge]",
  Idefics_9b = "Idefics_9b (Multimodal) [ml.g5.12xlarge]",
  Idefics_80b = "Idefics_80b (Multimodal) [ml.g5.48xlarge]",
}

export interface SystemConfig {
  knowledgeBase: {
    enabled: boolean;
    knowledgeBaseModels: {
      enabled: boolean;
      ecrRepository: string;
      ecrImageTag: string;
    };
  };
  llms: {};
  rag: {
    enabled: boolean;
    engines: {
      opensearch: {
        enabled: boolean;
      };
      smartsearch: {
        enabled: boolean;
      };
    };
    embeddingsModels: string[];
    crossEncoderModels: string[];
  };
  sagemaker: {
    modelAssetsBucket: string;
  };
  ui: {
    enabled: boolean;
  };
}

export interface SageMakerLLMEndpoint {
  name: string;
  endpoint: sagemaker.CfnEndpoint;
}