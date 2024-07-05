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

import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";
import { DynamoDBTable } from "../shared/table";

export class DynamoDBConstruct extends Construct {
  public sessionTableName: string;
  public messageTableName: string;
  public promptTableName: string;
  public indexTableName: string;
  public modelTableName: string;
  public intentionTableName: string;

  public readonly byUserIdIndex: string = "byUserId";
  public readonly bySessionIdIndex: string = "bySessionId";
  public readonly byTimestampIndex: string = "byTimestamp";

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const sessionIdAttr = {
      name: "sessionId",
      type: dynamodb.AttributeType.STRING,
    }
    const userIdAttr = {
      name: "userId",
      type: dynamodb.AttributeType.STRING,
    }
    const groupNameAttr = {
      name: "groupName",
      type: dynamodb.AttributeType.STRING,
    }
    const messageIdAttr = {
      name: "messageId",
      type: dynamodb.AttributeType.STRING,
    }
    const timestampAttr = {
      name: "createTimestamp",
      type: dynamodb.AttributeType.STRING,
    }
    // Need to be unified
    const groupNameAttr2 = {
      name: "GroupName",
      type: dynamodb.AttributeType.STRING,
    }
    const sortKeyAttr = {
      name: "SortKey",
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
    const intentionIdAttr = {
      name: "intentionId",
      type: dynamodb.AttributeType.STRING,
    }

    const sessionsTable = new DynamoDBTable(this, "Session", sessionIdAttr, userIdAttr).table;
    sessionsTable.addGlobalSecondaryIndex({
      indexName: this.byTimestampIndex,
      partitionKey: userIdAttr,
      sortKey: timestampAttr,
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const messagesTable = new DynamoDBTable(this, "Message", messageIdAttr, sessionIdAttr).table;
    messagesTable.addGlobalSecondaryIndex({
      indexName: this.bySessionIdIndex,
      partitionKey: { name: "sessionId", type: dynamodb.AttributeType.STRING },
    });

    const promptTable = new DynamoDBTable(this, "Prompt", groupNameAttr2, sortKeyAttr).table;
    const indexTable = new DynamoDBTable(this, "Index", groupNameAttr, indexIdAttr).table;
    const modelTable = new DynamoDBTable(this, "Model", groupNameAttr, modelIdAttr).table;
    const intentionTable = new DynamoDBTable(this, "Intention", groupNameAttr, intentionIdAttr).table;

    this.sessionTableName = sessionsTable.tableName;
    this.messageTableName = messagesTable.tableName;
    this.promptTableName = promptTable.tableName;
    this.indexTableName = indexTable.tableName;
    this.modelTableName = modelTable.tableName;
    this.intentionTableName = intentionTable.tableName;
  }
}
