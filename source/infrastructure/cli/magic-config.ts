#!/usr/bin/env node

import { Command } from "commander";
import { prompt } from "enquirer";
import * as fs from "fs";
import * as AWS from "aws-sdk";
import {
  SystemConfig,
  SupportedBedrockRegion,
  SupportedRegion,
} from "../lib/shared/types";
import { LIB_VERSION } from "./version.js";

const embeddingModels = [
  {
    provider: "bedrock",
    name: "amazon.titan-embed-text-v2:0",
    commitId: "",
    dimensions: 1024,
    default: true,
  },
  {
    provider: "bedrock",
    name: "cohere.embed-english-v3",
    commitId: "",
    dimensions: 1024,
  },
  {
    provider: "bedrock",
    name: "amazon.titan-embed-text-v1",
    commitId: "",
    dimensions: 1024,
  },
  {
    provider: "sagemaker",
    name: "bce-embedding-and-bge-reranker",
    commitId: "43972580a35ceacacd31b95b9f430f695d07dde9",
    dimensions: 768,
  }
];

const supportedRegions = Object.values(SupportedRegion) as string[];
const supportedBedrockRegions = Object.values(SupportedBedrockRegion) as string[];

const llms = [
  {
    provider: "bedrock",
    name: "anthropic.claude-3-sonnet-20240229-v1:0",
  }
]

// Function to get AWS account ID and region
async function getAwsAccountAndRegion() {
  const sts = new AWS.STS();
  let AWS_ACCOUNT;
  let AWS_REGION;
  try {
    const data = await sts.getCallerIdentity().promise();
    AWS_ACCOUNT = data.Account;
  } catch (error) {
    console.error('Error getting AWS account:', error);
    throw error;
  }
  try {
    AWS.config.credentials = new AWS.SharedIniFileCredentials({ profile: "default" });
    AWS_REGION = new AWS.IniLoader().loadFrom({ isConfig: true }).default.region;

  } catch (error) {
    console.error("No default region found in the AWS credentials file. Please enter the region you want to deploy the intelli-agent solution");
    AWS_REGION = undefined;
  }

  console.log("AWS_ACCOUNT", AWS_ACCOUNT);
  console.log("AWS_REGION", AWS_REGION);
  return { AWS_ACCOUNT, AWS_REGION };
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
      options.prefix = config.prefix;
      options.intelliAgentUserEmail = config.email;
      options.intelliAgentDeployRegion = config.deployRegion;
      options.enableKnowledgeBase = config.knowledgeBase.enabled;
      options.knowledgeBaseType = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled
        ? "intelliAgentKb"
        : "bedrockKb";
      options.intelliAgentUserEmail = config.email;
      options.intelliAgentKbVectorStoreType = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.enabled
        ? "opensearch"
        : "unsupported";
      options.useCustomDomain = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.useCustomDomain;
      options.customDomainEndpoint = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.customDomainEndpoint;
      options.enableIntelliAgentKbModel = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.enabled;
      options.knowledgeBaseModelEcrRepository = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrRepository;
      options.knowledgeBaseModelEcrImageTag = config.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrImageTag;
      options.enableChat = config.chat.enabled;
      options.bedrockRegion = config.chat.bedrockRegion;
      options.enableConnect = config.chat.amazonConnect.enabled;
      options.defaultEmbedding = config.model.embeddingsModels && config.model.embeddingsModels.length > 0
        ? config.model.embeddingsModels[0].name
        : embeddingModels[0].name;
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
  const mandatoryQuestions = [
    {
      type: "input",
      name: "prefix",
      message: "Prefix to differentiate this deployment",
      initial: options.prefix,
      askAnswered: false,
    },
    {
      type: "input",
      name: "intelliAgentUserEmail",
      message: "Please enter the name of the email you want to use for notifications",
      initial: options.intelliAgentUserEmail ?? "support@example.com",
      validate(intelliAgentUserEmail: string) {
        return (this as any).skipped ||
          RegExp(/^[a-zA-Z0-9]+([._-][0-9a-zA-Z]+)*@[a-zA-Z0-9]+([.-][0-9a-zA-Z]+)*\.[a-zA-Z]{2,}$/i).test(intelliAgentUserEmail)
          ? true
          : "Enter a valid email address in specified format: [a-zA-Z0-9]+([._-][0-9a-zA-Z]+)*@[a-zA-Z0-9]+([.-][0-9a-zA-Z]+)*\\.[a-zA-Z]{2,}";
      },
    },
    {
      type: "input",
      name: "intelliAgentDeployRegion",
      message: "Please enter the region you want to deploy the intelli-agent solution",
      initial: options.intelliAgentDeployRegion ?? AWS_REGION,
      validate(intelliAgentDeployRegion: string) {
        if (Object.values(supportedRegions).includes(intelliAgentDeployRegion)) {
          return true;
        }
        return "Enter a valid region. Supported regions: " + supportedRegions.join(", ");
      },
    },
  ]

  const mandatoryQuestionAnswers: any = await prompt(mandatoryQuestions);

  let questions = [
    {
      type: "confirm",
      name: "enableKnowledgeBase",
      message: "Do you want to use knowledge base in this solution?",
      initial: options.enableKnowledgeBase ?? false,
    },
    {
      type: "select",
      name: "knowledgeBaseType",
      hint: "ENTER to confirm selection",
      message: "Which knowledge base type do you want to use?",
      choices: [
        { message: "Intelli-Agent Knowledge Base", name: "intelliAgentKb" },
        // { message: "Bedrock Knowledge Base (To Be Implemented)", name: "bedrockKb" },
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
        return (!(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb");
      },
      initial: options.intelliAgentKbVectorStoreType ?? "opensearch",
    },
    {
      type: "confirm",
      name: "useCustomDomain",
      message: "Do you want to use a custom domain for your knowledge base?",
      initial: options.useCustomDomain ?? false,
      skip(): boolean {
        if ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb" ||
          (this as any).state.answers.intelliAgentKbVectorStoreType !== "opensearch") {
          return true;
        }
        return false;
      },
    },
    {
      type: "input",
      name: "customDomainEndpoint",
      message: "Please enter the endpoint of the custom domain",
      initial: options.customDomainEndpoint ?? "",
      validate(customDomainEndpoint: string) {
        return (this as any).skipped ||
          RegExp(/^https:\/\/[a-z0-9-]+.[a-z0-9-]{2,}\.es\.amazonaws\.com$/).test(customDomainEndpoint)
          ? true
          : "Enter a valid OpenSearch domain endpoint (e.g., https://search-domain-region-id.region.es.amazonaws.com)";
      },
      skip(): boolean {
        if ( !(this as any).state.answers.enableKnowledgeBase ||
          (this as any).state.answers.knowledgeBaseType !== "intelliAgentKb" ||
          (this as any).state.answers.intelliAgentKbVectorStoreType !== "opensearch" ||
          !(this as any).state.answers.useCustomDomain) {
          return true;
        }
        return false;
      },
    },
    {
      type: "confirm",
      name: "enableIntelliAgentKbModel",
      message: "Do you want to inject PDF files into your knowledge base?",
      initial: options.enableIntelliAgentKbModel ?? true,
      skip(): boolean {
        return (!(this as any).state.answers.enableKnowledgeBase ||
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
        return (!(this as any).state.answers.enableKnowledgeBase ||
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
        return (!(this as any).state.answers.enableKnowledgeBase ||
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
      type: "input",
      name: "bedrockRegion",
      message: "Which region would you like to use Bedrock?",
      initial: options.bedrockRegion ?? mandatoryQuestionAnswers.intelliAgentDeployRegion,
      validate(bedrockRegion: string) {
        if (Object.values(supportedBedrockRegions).includes(bedrockRegion)) {
          return true;
        }
        return "Enter a valid region for Bedrock. Supported regions: " + supportedBedrockRegions.join(", ");
      },
      skip(): boolean {
        return (!(this as any).state.answers.enableChat);
      },
    },
    {
      type: "confirm",
      name: "enableConnect",
      message: "Do you want to integrate it with Amazon Connect?",
      initial: options.enableConnect ?? true,
      skip(): boolean {
        return (!(this as any).state.answers.enableChat);
      },
    },
    {
      type: "select",
      name: "defaultEmbedding",
      message: "Select an embedding model, it is used when injecting and retrieving knowledges or intentions",
      choices: embeddingModels.map((m) => ({ name: m.name, value: m })),
      initial: options.defaultEmbedding,
      validate(value: string) {
        if ((this as any).state.answers.enableChat) {
          return value ? true : "Select a default embedding model";
        }

        return true;
      },
      skip(): boolean {
        return (!(this as any).state.answers.enableKnowledgeBase &&
          !(this as any).state.answers.enableChat);
      },
    },
    // {
    //   type: "select",
    //   name: "defaultLlm",
    //   message: "Select a llm model",
    //   choices: llms.map((m) => ({ name: m.name, value: m })),
    //   initial: options.defaultLlm,
    //   validate(value: string) {
    //     if ((this as any).state.answers.enableChat) {
    //       return value ? true : "Select a default llm model";
    //     }

    //     return true;
    //   },
    //   skip(): boolean {
    //     return !(this as any).state.answers.enableChat;
    //   },
    // },
    {
      type: "input",
      name: "sagemakerModelS3Bucket",
      message: "Please enter the name of the S3 Bucket for the sagemaker models assets",
      initial: options.sagemakerModelS3Bucket ?? `intelli-agent-models-${AWS_ACCOUNT}-${mandatoryQuestionAnswers.intelliAgentDeployRegion}`,
      validate(sagemakerModelS3Bucket: string) {
        return (this as any).skipped ||
          RegExp(/^(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/i).test(sagemakerModelS3Bucket)
          ? true
          : "Enter a valid S3 Bucket Name in the specified format: (?!^xn--|.+-s3alias$)^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]";
      },
      skip(): boolean {
        return (this as any).state.answers.defaultEmbedding !== "bce-embedding-and-bge-reranker";
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
        // { message: "Authing", name: "authing" },
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
    prefix: mandatoryQuestionAnswers.prefix,
    email: mandatoryQuestionAnswers.intelliAgentUserEmail,
    deployRegion: mandatoryQuestionAnswers.intelliAgentDeployRegion,
    knowledgeBase: {
      enabled: answers.enableKnowledgeBase,
      knowledgeBaseType: {
        intelliAgentKb: {
          enabled: answers.knowledgeBaseType === "intelliAgentKb",
          vectorStore: {
            opensearch: {
              enabled: answers.intelliAgentKbVectorStoreType === "opensearch",
              useCustomDomain: answers.useCustomDomain,
              customDomainEndpoint: answers.customDomainEndpoint,
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
      bedrockRegion: answers.bedrockRegion,
      amazonConnect: {
        enabled: answers.enableConnect,
      },
    },
    model: {
      embeddingsModels: embeddingModels.filter(model => model.name === answers.defaultEmbedding),
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
        // authing: {
        //   enabled: advancedSettings.federatedAuthProvider === "authing",
        // },
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

