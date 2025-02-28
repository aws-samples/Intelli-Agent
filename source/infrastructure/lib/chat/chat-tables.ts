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

export class ChatTablesConstruct extends Construct {
  public sessionsTableName: string;
  public messagesTableName: string;
  public promptTableName: string;
  public intentionTableName: string;
  public stopSignalsTableName: string;

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
    const intentionIdAttr = {
      name: "intentionId",
      type: dynamodb.AttributeType.STRING,
    }
    const wsConnectionIdAttr = {
      name: "wsConnectionId",
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
    const intentionTable = new DynamoDBTable(this, "Intention", groupNameAttr, intentionIdAttr).table;
    const stopSignalsTable = new DynamoDBTable(this, "StopSignals", wsConnectionIdAttr).table;

    this.sessionsTableName = sessionsTable.tableName;
    this.messagesTableName = messagesTable.tableName;
    this.promptTableName = promptTable.tableName;
    this.intentionTableName = intentionTable.tableName;
    this.stopSignalsTableName = stopSignalsTable.tableName;
  }
}
