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

    // // Create the Lambda functions
    // const postFn = new lambda.Function(this, "PostRatingFunction", {
    //   runtime:lambda.Runtime.PYTHON_3_7,
    //   handler: "rating.lambda_handler",
    //   code: Code.fromAsset(join(__dirname, "../../../lambda/ddb")),
    //   environment: {
    //     SESSIONS_TABLE_NAME: sessionsTable.tableName,
    //     SESSIONS_BY_USER_ID_INDEX_NAME: this.byUserIdIndex,
    //   },
    //   vpc: _vpc,
    //     vpcSubnets: {
    //         subnets: _vpc.privateSubnets,
    //     },
    //     securityGroups: [props._securityGroup]
    // });

    // postFn.addToRolePolicy(new iam.PolicyStatement({
    //         actions: [
    //         "dynamodb:*"
    //         ],
    //         effect: iam.Effect.ALLOW,
    //         resources: ['*'],
    //         }
    //     ))

    
    // // Grant permissions to the Lambda functions to access the DynamoDB table
    // sessionsTable.grantReadWriteData(postFn);

    // const api = new apigw.RestApi(this, 'ddbApi', {
    //     restApiName: 'ddbApi',
    //     description: 'This service serves the dynamodb which stores the data of model rating.',
    //     endpointConfiguration: {
    //         types: [apigw.EndpointType.REGIONAL]
    //     },
    //     defaultCorsPreflightOptions: {
    //         allowHeaders: [
    //             'Content-Type',
    //             'X-Amz-Date',
    //             'Authorization',
    //             'X-Api-Key',
    //             'X-Amz-Security-Token'
    //         ],
    //         allowMethods: apigw.Cors.ALL_METHODS,
    //         allowCredentials: true,
    //         allowOrigins: apigw.Cors.ALL_ORIGINS,
    //     },
    //     deployOptions: {
    //         stageName: 'v1',
    //         metricsEnabled: true,
    //         loggingLevel: apigw.MethodLoggingLevel.INFO,
    //         dataTraceEnabled: true,
    //         tracingEnabled: true,
    //     },
    // });
    // // Define the API resources and methods
    // const session = api.root.addResource('rating');
    // session.addMethod("POST", new LambdaIntegration(postFn));
  
    this._chatSessionTable = sessionsTable.tableName;
  }
}
