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
  }
];

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
      options.enableRag = config.rag.enabled;
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
      name: "enableKnowledgeBaseConstruction",
      message: "Do you want to construct a knowledge base using this solution?",
      initial: options.enableKnowledgeBaseConstruction || true,
    },
    {
      type: "confirm",
      name: "enableKnowledgeBaseModels",
      message: "Do you want to use Sagemaker Models to enhance the construction of the knowledge base?",
      initial: options.enableKnowledgeBaseModels || true,
      skip(): boolean {
        return !(this as any).state.answers.enableKnowledgeBaseConstruction;
      },
    },
    {
      type: "input",
      name: "knowledgeBaseModelEcrRepository",
      message: "Please enter the name of the ECR Repository for the knowledge base model",
      initial: options.knowledgeBaseModelEcrRepository || "intelli-agent-knowledge-base",
      validate(knowledgeBaseModelEcrRepository: string) {
        return (this as any).skipped ||
          RegExp(/^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*)*[a-z0-9]+(?:[._-][a-z0-9]+)*$/i).test(knowledgeBaseModelEcrRepository)
          ? true
          : "Enter a valid ECR Repository Name in the specified format: (?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*";
      },
      skip(): boolean {
        return (!(this as any).state.answers.enableKnowledgeBaseModels ||
          !(this as any).state.answers.enableKnowledgeBaseConstruction);
      }
    },
    {
      type: "input",
      name: "knowledgeBaseModelEcrImageTag",
      message: "Please enter the ECR Image Tag for the knowledge base model",
      initial: options.knowledgeBaseModelEcrImageTag || "latest",
      validate(knowledgeBaseModelEcrImageTag: string) {
        return (this as any).skipped ||
          (RegExp(/^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*)*[a-z0-9]+(?:[._-][a-z0-9]+)*$/i)).test(knowledgeBaseModelEcrImageTag)
          ? true
          : "Enter a valid ECR Image Tag in the specified format: ";
      },
      skip(): boolean {
        return (!(this as any).state.answers.enableKnowledgeBaseModels ||
          !(this as any).state.answers.enableKnowledgeBaseConstruction);
      }
    },
    {
      type: "confirm",
      name: "enableRag",
      message: "Do you want to enable RAG",
      initial: options.enableRag || false,
    },
    {
      type: "select",
      name: "ragsToEnable",
      hint: "SPACE to select, ENTER to confirm selection",
      message: "Which datastores do you want to enable for RAG",
      choices: [
        { message: "OpenSearch", name: "opensearch" },
        { message: "SmartSearch Guidance (Working In Porgress)", name: "smartsearch" },
      ],
      validate(value: string) {
        if ((this as any).state.answers.enableRag) {
          return value ? true : "Select a rag engine";
        }

        return true;
      },
      skip(): boolean {
        return !(this as any).state.answers.enableRag;
      },
      initial: options.ragsToEnable || [],
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
        return (
          !(this as any).state.answers.enableRag || !(this as any).state.answers.ragsToEnable.includes("opensearch")
        );
      },
    },
    {
      type: "input",
      name: "sagemakerModelS3Bucket",
      message: "Please enter the name of the S3 Bucket for the sagemaker models assets",
      initial: options.sagemakerModelS3Bucket || `intelli-agent-models-${AWS_ACCOUNT}-${AWS_REGION}`,
      validate(sagemakerModelS3Bucket: string) {
        return (this as any).skipped ||
          RegExp(/^(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/i).test(sagemakerModelS3Bucket)
          ? true
          : "Enter a valid S3 Bucket Name in the specified format: (?!^xn--|.+-s3alias$)^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]";
      },
      skip(): boolean {
        return !(this as any).state.answers.enableRag;
      }
    },
    {
      type: "confirm",
      name: "enableUI",
      message: "Do you want to create a UI for the chatbot",
      initial: options.enableUI || false,
    },
  ];
  const answers: any = await prompt(questions);

  // Create the config object
  const config = {
    knowledgeBase: {
      enabled: answers.enableKnowledgeBaseConstruction,
      knowledgeBaseModels: {
        enabled: answers.enableKnowledgeBaseModels,
        ecrRepository: answers.knowledgeBaseModelEcrRepository,
        ecrImageTag: answers.knowledgeBaseModelEcrImageTag,
      }
    },
    llms: {},
    rag: {
      enabled: answers.enableRag,
      engines: {
        opensearch: {
          enabled: answers.ragsToEnable.includes("opensearch"),
        },
        smartsearch: {
          enabled: answers.ragsToEnable.includes("smartsearch"),
        },
      },
      embeddingsModels: [answers.defaultEmbedding],
      crossEncoderModels: [],
    },
    sagemaker: {
      modelAssetsBucket: answers.sagemakerModelS3Bucket,
    },
    ui: {
      enabled: answers.enableUI,
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