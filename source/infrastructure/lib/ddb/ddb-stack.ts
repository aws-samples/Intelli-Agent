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

interface ddbStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
}

export class DynamoDBStack extends NestedStack {

  _chatSessionTable;
  public readonly byUserIdIndex: string = "byUserId";

  constructor(scope: Construct, id: string, props: ddbStackProps) {
    super(scope, id, props);
    const _vpc = props._vpc;
    
    // Create the DynamoDB table
    const sessionsTable = new dynamodb.Table(this, "SessionsTable", {
      partitionKey: {
        name: "SessionId",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "UserId",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    sessionsTable.addGlobalSecondaryIndex({
      indexName: this.byUserIdIndex,
      partitionKey: { name: "UserId", type: dynamodb.AttributeType.STRING },
    });
  
    this._chatSessionTable = sessionsTable.tableName;
  }
}
