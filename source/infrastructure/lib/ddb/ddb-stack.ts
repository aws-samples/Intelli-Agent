import {
  Duration, NestedStack, RemovalPolicy, StackProps
} from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Stream, StreamEncryption } from "aws-cdk-lib/aws-kinesis";
import { Construct } from "constructs";

interface DDBStackProps extends StackProps {
  stackVpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
}

export class DynamoDBStack extends NestedStack {

  public sessionTableName;
  public messageTableName;
  public readonly byUserIdIndex: string = "byUserId";
  public readonly bySessionIdIndex: string = "bySessionId";

  constructor(scope: Construct, id: string, props: DDBStackProps) {
    super(scope, id, props);

    // Create DynamoDB table
    const sessionsTable = new dynamodb.Table(this, "SessionsTable", {
      partitionKey: {
        name: "sessionId",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "userId",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    sessionsTable.addGlobalSecondaryIndex({
      indexName: this.byUserIdIndex,
      partitionKey: { name: "userId", type: dynamodb.AttributeType.STRING },
    });

    const messagesTable = new dynamodb.Table(this, "MessagesTable", {
      partitionKey: {
        name: "messageId",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "sessionId",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    messagesTable.addGlobalSecondaryIndex({
      indexName: this.bySessionIdIndex,
      partitionKey: { name: "sessionId", type: dynamodb.AttributeType.STRING },
    });

    this.sessionTableName = sessionsTable.tableName;
    this.messageTableName = messagesTable.tableName;

  }
}
