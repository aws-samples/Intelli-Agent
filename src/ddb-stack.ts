import { NestedStack, StackProps, Duration, CfnOutput,NestedStackProps, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import { Table, AttributeType } from "aws-cdk-lib/aws-dynamodb";
import { Function, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import { LambdaIntegration, RestApi } from "aws-cdk-lib/aws-apigateway";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import { join } from "path";

interface ddbStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
}

export class DynamoDBStack extends NestedStack {

  _chatSessionTable;
  constructor(scope: Construct, id: string, props: ddbStackProps) {
    super(scope, id, props);
    const _vpc = props._vpc;
    
    // Create the DynamoDB table
    const table = new Table(this, "modelRatingTable", {
      tableName: "modelRatingInfo",
      partitionKey: {
        name: "session_id",
        type: AttributeType.STRING,
      },
    //   removalPolicy: RemovalPolicy.DESTROY, 
    });

    // Create the Lambda functions
    const postFn = new lambda.Function(this, "PostRatingFunction", {
      runtime:lambda.Runtime.PYTHON_3_7,
      handler: "rating.lambda_handler",
      code: Code.fromAsset(join(__dirname, "../src/lambda/ddb")),
      environment: {
        TABLE_NAME: table.tableName,
      },
      vpc: _vpc,
        vpcSubnets: {
            subnets: _vpc.privateSubnets,
        },
        securityGroups: [props._securityGroup]
    });

    postFn.addToRolePolicy(new iam.PolicyStatement({
            actions: [
            "dynamodb:*"
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
            }
        ))

    
    // Grant permissions to the Lambda functions to access the DynamoDB table
    table.grantReadWriteData(postFn);
   

    const api = new apigw.RestApi(this, 'ddbApi', {
        restApiName: 'ddbApi',
        description: 'This service serves the dynamodb which stores the data of model rating.',
        endpointConfiguration: {
            types: [apigw.EndpointType.REGIONAL]
        },
        deployOptions: {
            stageName: 'v1',
            metricsEnabled: true,
            loggingLevel: apigw.MethodLoggingLevel.INFO,
            dataTraceEnabled: true,
            tracingEnabled: true,
        },
    });
    // Define the API resources and methods
    const session = api.root.addResource('rating');
    session.addMethod("POST", new LambdaIntegration(postFn));
  
    this._chatSessionTable = table.tableName;
  }
}
