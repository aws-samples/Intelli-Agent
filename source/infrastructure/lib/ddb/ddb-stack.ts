import { NestedStack, StackProps, Duration, CfnOutput,NestedStackProps, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import { Function, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import { LambdaIntegration, RestApi } from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import { join } from "path";
import { Stream, StreamEncryption } from "aws-cdk-lib/aws-kinesis";

interface ddbStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
}

export class DynamoDBStack extends NestedStack {

  _sessionsTableName;
  _messagesTableName;
  public readonly byUserIdIndex: string = "byUserId";
  public readonly bySessionIdIndex: string = "bySessionId";

  constructor(scope: Construct, id: string, props: ddbStackProps) {
    super(scope, id, props);
    const _vpc = props._vpc;

    const sessionsTableStream = new Stream(this, `SessionsTableKinesisStream`, {
      shardCount: 1,
      retentionPeriod: Duration.days(7),
      encryption: StreamEncryption.MANAGED,
    });

    const messagesTableStream = new Stream(this, `MessagesTableKinesisStream`, {
      shardCount: 1,
      retentionPeriod: Duration.days(7),
      encryption: StreamEncryption.MANAGED,
    });
    
    // Create the DynamoDB table
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
      kinesisStream: sessionsTableStream,
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
      kinesisStream: messagesTableStream,
    });

    messagesTable.addGlobalSecondaryIndex({
      indexName: this.bySessionIdIndex,
      partitionKey: { name: "sessionId", type: dynamodb.AttributeType.STRING },
    });

    this._sessionsTableName = sessionsTable.tableName;
    this._messagesTableName = messagesTable.tableName;

  }
}
