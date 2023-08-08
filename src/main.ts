import { App, CfnOutput, Stack, StackProps, CfnParameter } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { VpcStack } from './vpc-stack';
import { Ec2Stack } from './ec2-stack';
import { OpenSearchStack } from './os-stack';
import { LLMApiStack } from './api-stack';
import { DynamoDBStack } from './ddb-stack';
import { LLMStack } from './llm-stack';
import { AssetsStack } from './assets-stack';

import * as dotenv from "dotenv";
dotenv.config();

export class RootStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    // add cdk input parameters for user to specify s3 bucket store model assets
    const _S3ModelAssets = new CfnParameter(this, 'S3ModelAssets', {
      type: 'String',
      description: 'S3 Bucket for model & code assets',
      default: 'llm-rag',
    });

    const _VpcStack = new VpcStack(this, 'vpc-stack', {env:process.env});

    const _OsStack = new OpenSearchStack(this,'os-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup});
    _OsStack.addDependency(_VpcStack);

    const _Ec2Stack = new Ec2Stack(this, 'ec2-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup, _domainEndpoint:_OsStack._domainEndpoint, env:process.env});
    _Ec2Stack.addDependency(_VpcStack);
    _Ec2Stack.addDependency(_OsStack);

    const _ApiStack = new LLMApiStack(this, 'api-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup, _domainEndpoint:_OsStack._domainEndpoint, env:process.env});
    _ApiStack.addDependency(_VpcStack);
    _ApiStack.addDependency(_OsStack);

    const _DynamoDBStack = new DynamoDBStack(this, 'ddb-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup, _domainEndpoint:_OsStack._domainEndpoint, env:process.env});
    _DynamoDBStack.addDependency(_VpcStack);
    _DynamoDBStack.addDependency(_OsStack);

    // This assest stack is to mitigate issue that the model assets in s3 bucket can't be located immediately to create sagemaker model
    const _AssetsStack = new AssetsStack(this, 'assets-stack', {_s3ModelAssets:_S3ModelAssets.valueAsString, env:process.env});
    const _LLMStack = new LLMStack(this, 'llm-stack', {
        _s3ModelAssets:_S3ModelAssets.valueAsString,
        _crossCodePrefix:_AssetsStack._crossCodePrefix,
        _embeddingCodePrefix:_AssetsStack._embeddingCodePrefix,
        _instructCodePrefix:_AssetsStack._instructCodePrefix,
        env:process.env
    });
    _LLMStack.addDependency(_AssetsStack);

    new CfnOutput(this, 'VPC',{value:_VpcStack._vpc.vpcId});
    new CfnOutput(this, 'OpenSearch Endpoint',{value:_OsStack._domainEndpoint});
    // contatenate the outputs from the ec2 stack with port 8081 and prefix _dashboards
    new CfnOutput(this, 'OpenSearch Dashboard',{value:`${_Ec2Stack._publicIP}:8081/_dashboards`});
    new CfnOutput(this, 'Cross Model Endpoint',{value:_LLMStack._crossEndPointName || 'No Cross Endpoint Created'});
    new CfnOutput(this, 'Embedding Model Endpoint',{value:_LLMStack._embeddingEndPointName || 'No Embedding Endpoint Created'});
    new CfnOutput(this, 'Instruct Model Endpoint',{value:_LLMStack._instructEndPointName || 'No Instruct Endpoint Created'});
  }
}

// for development, use account/region from cdk cli
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

new RootStack(app, 'llm-bot-dev', { env: devEnv });

app.synth();