/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import { RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from "constructs";
import * as dotenv from "dotenv";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";

import { SystemConfig } from "./types";
import { IAMHelper } from "./iam-helper";
import { DynamoDBTable } from "./table";
import { VpcConstruct } from "./vpc-construct";
import { Vpc, SecurityGroup } from 'aws-cdk-lib/aws-ec2';

dotenv.config();

export interface SharedConstructProps {
  readonly config: SystemConfig;
}

export interface SharedConstructOutputs {
  iamHelper: IAMHelper;
  vpc: Vpc;
  securityGroup: SecurityGroup;
  chatbotTable: dynamodb.Table;
  indexTable: dynamodb.Table;
  modelTable: dynamodb.Table;
  resultBucket: s3.Bucket;
}

export class SharedConstruct extends Construct implements SharedConstructOutputs {
  public iamHelper: IAMHelper;
  public vpc: Vpc;
  public securityGroup: SecurityGroup;
  public chatbotTable: dynamodb.Table;
  public indexTable: dynamodb.Table;
  public modelTable: dynamodb.Table;
  public resultBucket: s3.Bucket;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const iamHelper = new IAMHelper(this, "iam-helper");

    const vpcConstruct = new VpcConstruct(this, "vpc-construct");

    const groupNameAttr = {
      name: "groupName",
      type: dynamodb.AttributeType.STRING,
    }
    const indexIdAttr = {
      name: "indexId",
      type: dynamodb.AttributeType.STRING,
    }
    const modelIdAttr = {
      name: "modelId",
      type: dynamodb.AttributeType.STRING,
    }
    const chatbotIdAttr = {
      name: "chatbotId",
      type: dynamodb.AttributeType.STRING,
    }

    const chatbotTable = new DynamoDBTable(this, "Chatbot", groupNameAttr, chatbotIdAttr, true).table;
    const indexTable = new DynamoDBTable(this, "Index", groupNameAttr, indexIdAttr).table;
    const modelTable = new DynamoDBTable(this, "Model", groupNameAttr, modelIdAttr).table;

    const resultBucket = new s3.Bucket(this, "intelli-agent-result-bucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    this.iamHelper = iamHelper;
    this.vpc = vpcConstruct.vpc;
    this.securityGroup = vpcConstruct.securityGroup;
    this.chatbotTable = chatbotTable;
    this.indexTable = indexTable;
    this.modelTable = modelTable;
    this.resultBucket = resultBucket;
  }
}

