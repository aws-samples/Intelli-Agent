import { App, CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { VpcStack } from './vpc-stack';
import { Ec2Stack } from './ec2-stack';
import { OpenSearchStack } from './os-stack';
import { LLMApiStack } from './api-stack';

import * as dotenv from "dotenv";
dotenv.config();

export class MyStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    const _VpcStack = new VpcStack(this, 'vpc-stack', {env:process.env});

    const _OsStack = new OpenSearchStack(this,'os-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup});
    _OsStack.addDependency(_VpcStack);

    const _Ec2Stack = new Ec2Stack(this, 'ec2-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup, _domainEndpoint:_OsStack._domainEndpoint, env:process.env});
    _Ec2Stack.addDependency(_VpcStack);
    _Ec2Stack.addDependency(_OsStack);

    const _ApiStack = new LLMApiStack(this, 'api-stack', {_vpc:_VpcStack._vpc, _securityGroup:_VpcStack._securityGroup, _domainEndpoint:_OsStack._domainEndpoint, env:process.env});
    _ApiStack.addDependency(_VpcStack);
    _ApiStack.addDependency(_OsStack);

    new CfnOutput(this,'VPC',{value:_VpcStack._vpc.vpcId});
    new CfnOutput(this,'OpenSearch endpoint',{value:_OsStack._domainEndpoint});

  }
}

// for development, use account/region from cdk cli
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

new MyStack(app, 'llm-bot-dev', { env: devEnv });
// new MyStack(app, 'llm-bot-prod', { env: prodEnv });

app.synth();