#!/usr/bin/env node

import { Command } from "commander";
import { prompt } from "enquirer";
import * as fs from "fs";
import * as AWS from "aws-sdk";
import {
  SystemConfig
} from "./types";
import { LIB_VERSION } from "./version.js";

const embeddingModels = [
  {
    provider: "sagemaker",
    name: "maidalun1020/bce-embedding-base_v1",
    dimensions: 1024,
    default: true,
  }
];

const llms = [
  {
    provider: "bedrock",
    name: "anthropic.claude-3-sonnet-20240229-v1:0",
  }
]

// Use AWS SDK to get the account and region
AWS.config.credentials = new AWS.SharedIniFileCredentials({ profile: "default" });
AWS.config.region = new AWS.IniLoader().loadFrom({ isConfig: true }).default.region;


// Function to get AWS account ID and region
async function getAwsAccountAndRegion() {
  const sts = new AWS.STS();
  try {
    const data = await sts.getCallerIdentity().promise();
    const AWS_ACCOUNT = data.Account;
    const AWS_REGION = AWS.config.region;

    return { AWS_ACCOUNT, AWS_REGION };
  } catch (error) {
    console.error('Error getting AWS account and region:', error);
    throw error;
  }
}


/**
 * Main entry point
 */

(async () => {
  let program = new Command().description(
    "Creates a new chatbot configuration"
  );
  program.version(LIB_VERSION);

  program.option("-p, --prefix <prefix>", "The prefix for the stack");

  program.action(async (options) => {
    if (fs.existsSync("./bin/config.json")) {
      const config: SystemConfig = JSON.parse(
        fs.readFileSync("./bin/config.json").toString("utf8")
      );
      options.enableKnowledgeBase = config.knowledgeBase.enabled;
      options.knowledgeBaseType = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled
        ? "intelliAgentKb"
        : "bedrockKb";
      options.intelliAgentKbVectorStoreType = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.enabled
        ? "opensearch"
        : "unsupported";
      options.enableIntelliAgentKbModel = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.enabled;
      options.knowledgeBaseModelEcrRepository = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrRepository;
      options.knowledgeBaseModelEcrImageTag = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrImageTag;
      options.enableChat = config.chat.enabled;
      options.defaultEmbedding = (config.model.embeddingsModels ?? []).filter(
        (m: any) => m.default
      )[0].name;
      options.defaultLlm = config.model.llms.find((m) => m.provider === "bedrock")?.name;
      options.sagemakerModelS3Bucket = config.model.modelConfig.modelAssetsBucket;
      options.enableUI = config.ui.enabled;
      options.cognitoFederationEnabled = config.federatedAuth.enabled;
      options.cognitoFederationProvider = config.federatedAuth.provider.cognito.enabled
        ? "cognito"
        : "authing";

    }
    try {
      await processCreateOptions(options);
    } catch (err: any) {
      console.error("Could not complete the operation.");
      console.error(err.message);
      process.exit(1);
    }
  });

  program.parse(process.argv);
})();

function createConfig(config: any): void {
  fs.writeFileSync("./bin/config.json", JSON.stringify(config, undefined, 2));
  console.log("Configuration written to ./bin/config.json");
}

/**
 * Prompts the user for missing options
 *
 * @param options Options provided via the CLI
 * @returns The complete options
 */
async function processCreateOptions(options: any): Promise<void> {
  // Get AWS account ID and region
  const { AWS_ACCOUNT, AWS_REGION } = await getAwsAccountAndRegion();
  let questions = [
    {
      type: "confirm",
      name: "enableKnowledgeBase",
      message: "Do you want to use knowledge base in this solution?",
      initial: options.enableKnowledgeBase ?? true,
    },
    {
      type: "select",
      name: "knowledgeBaseType",
      hint: "ENTER to confirm selection",
      message: "Which knowledge base type do you want to use?",
      choices: [
        { message: "Intelli-Agent Knowledge Base", name: "intelliAgentKb" },
        { message: "Bedrock Knowledge Base (To Be Implemented)", name: "bedrockKb" },
      ],
      validate(value: string) {
        if ((this as any).state.answers.enableKnowledgeBase) {
          return value ? true : "Select a knowledge base type";
        }
        return true;
      },
      skip(): boolean {
        return !(this as any).state.answers.enableKnowledgeBase;
      },
      initial: options.knowledgeBaseType ?? "intelliAgentKb",
    },
    {
      type: "select",
      name: "intelliAgentKbVectorStoreType",
      hint: "ENTER to confirm selection",
      message: "Which vector store type do you want to use?",
      choices: [
        { message: "OpenSearch", name: "opensearch" },
      ],
      validate(value: string) {
        if ((this as any).state.answers.intelliAgentKbVectorStoreType) {
          return value ? true : "Select a vector store type";
        }

        return true;
      },
      skip(): boolean {
        return ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb");
      },
      initial: options.intelliAgentKbVectorStoreType ?? "opensearch",
    },
    {
      type: "confirm",
      name: "enableIntelliAgentKbModel",
      message: "Do you want to use Sagemaker Models to enhance the construction of the Intelli-Agent Knowledge Base?",
      initial: options.enableIntelliAgentKbModel ?? true,
      skip(): boolean {
        return ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb");
      },
    },
    {
      type: "input",
      name: "knowledgeBaseModelEcrRepository",
      message: "Please enter the name of the ECR Repository for the knowledge base model",
      initial: options.knowledgeBaseModelEcrRepository ?? "intelli-agent-knowledge-base",
      validate(knowledgeBaseModelEcrRepository: string) {
        return (this as any).skipped ||
          RegExp(/^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*)*[a-z0-9]+(?:[._-][a-z0-9]+)*$/i).test(knowledgeBaseModelEcrRepository)
          ? true
          : "Enter a valid ECR Repository Name in the specified format: (?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*";
      },
      skip(): boolean {
        return ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb" || 
          !(this as any).state.answers.enableIntelliAgentKbModel);
      },
    },
    {
      type: "input",
      name: "knowledgeBaseModelEcrImageTag",
      message: "Please enter the ECR Image Tag for the knowledge base model",
      initial: options.knowledgeBaseModelEcrImageTag ?? "latest",
      validate(knowledgeBaseModelEcrImageTag: string) {
        return (this as any).skipped ||
          (RegExp(/^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*)*[a-z0-9]+(?:[._-][a-z0-9]+)*$/i)).test(knowledgeBaseModelEcrImageTag)
          ? true
          : "Enter a valid ECR Image Tag in the specified format: ";
      },
      skip(): boolean {
        return ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb" || 
          !(this as any).state.answers.enableIntelliAgentKbModel);
      },
    },
    {
      type: "confirm",
      name: "enableChat",
      message: "Do you want to enable Chat?",
      initial: options.enableChat ?? true,
    },
    {
      type: "select",
      name: "defaultEmbedding",
      message: "Select a default sagemaker embedding model",
      choices: embeddingModels.map((m) => ({ name: m.name, value: m })),
      initial: options.defaultEmbedding,
      validate(value: string) {
        if ((this as any).state.answers.enableRag) {
          return value ? true : "Select a default embedding model";
        }

        return true;
      },
      skip(): boolean {
        return ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb" || 
          (this as any).state.answers.intelliAgentKbVectorStoreType !== "opensearch");
      },
    },
    {
      type: "select",
      name: "defaultLlm",
      message: "Select a default llm model",
      choices: llms.map((m) => ({ name: m.name, value: m })),
      initial: options.defaultLlm,
      validate(value: string) {
        if ((this as any).state.answers.enableChat) {
          return value ? true : "Select a default llm model";
        }

        return true;
      },
      skip(): boolean {
        return !(this as any).state.answers.enableChat;
      },
    },
    {
      type: "input",
      name: "sagemakerModelS3Bucket",
      message: "Please enter the name of the S3 Bucket for the sagemaker models assets",
      initial: options.sagemakerModelS3Bucket ?? `intelli-agent-models-${AWS_ACCOUNT}-${AWS_REGION}`,
      validate(sagemakerModelS3Bucket: string) {
        return (this as any).skipped ||
          RegExp(/^(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/i).test(sagemakerModelS3Bucket)
          ? true
          : "Enter a valid S3 Bucket Name in the specified format: (?!^xn--|.+-s3alias$)^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]";
      }
    },
    {
      type: "confirm",
      name: "enableUI",
      message: "Do you want to create a UI for the chatbot",
      initial: options.enableUI ?? true,
    },
  ];
  const answers: any = await prompt(questions);

  const advancedSettingsPrompts = [
    {
      type: "confirm",
      name: "enableFederatedAuth",
      message: "Do you want to enable Federated Authentication?",
      initial: options.cognitoFederationEnabled ?? true,
      skip(): boolean {
        return !answers.enableUI;
      }
    },
    {
      type: "select",
      name: "federatedAuthProvider",
      message: "Select a Federated Authentication Provider",
      choices: [
        { message: "Cognito", name: "cognito" },
        { message: "Authing", name: "authing" },
      ],
      initial: options.cognitoFederationProvider ?? "cognito",
      skip(): boolean {
        return (!(this as any).state.answers.enableFederatedAuth || !answers.enableUI);
      },
    },
  ];

  const doAdvancedConfirm: any = await prompt([
    {
      type: "confirm",
      name: "doAdvancedSettings",
      message: "Do you want to configure advanced settings?",
      initial: false,
    },
  ]);
  let advancedSettings: any = {};
  if (doAdvancedConfirm.doAdvancedSettings) {
    advancedSettings = await prompt(advancedSettingsPrompts);
  } else {
    advancedSettings = {
      enableFederatedAuth: true,
      federatedAuthProvider: "cognito",
    };
  }

  // Create the config object
  const config = {
    knowledgeBase: {
      enabled: answers.enableKnowledgeBase,
      knowledgeBaseType: {
        intelliAgentKb: {
          enabled: answers.knowledgeBaseType === "intelliAgentKb",
          vectorStore: {
            opensearch: {
              enabled: answers.intelliAgentKbVectorStoreType === "opensearch",
            },
          },
          knowledgeBaseModel: {
            enabled: answers.enableIntelliAgentKbModel,
            ecrRepository: answers.knowledgeBaseModelEcrRepository,
            ecrImageTag: answers.knowledgeBaseModelEcrImageTag,
          },
        },
      },
    },
    chat: {
      enabled: answers.enableChat,
    },
    model: {
      embeddingsModels: embeddingModels,
      llms: llms,
      modelConfig: {
        modelAssetsBucket: answers.sagemakerModelS3Bucket,
      },
    },
    ui: {
      enabled: answers.enableUI,
    },
    federatedAuth: {
      enabled: advancedSettings.enableFederatedAuth,
      provider: {
        cognito: {
          enabled: advancedSettings.federatedAuthProvider === "cognito",
        },
        authing: {
          enabled: advancedSettings.federatedAuthProvider === "authing",
        },
      },
    },
  };

  console.log("\n✨ This is the chosen configuration:\n");
  console.log(JSON.stringify(config, undefined, 4));
  (
    (await prompt([
      {
        type: "confirm",
        name: "create",
        message:
          "Do you want to create/update the configuration based on the above settings",
        initial: true,
      },
    ])) as any
  ).create
    ? createConfig(config)
    : console.log("Skipping");
}