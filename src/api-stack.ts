import { NestedStack, StackProps, Duration } from 'aws-cdk-lib';
import { DockerImageFunction }  from 'aws-cdk-lib/aws-lambda';
import { DockerImageCode, Architecture } from 'aws-cdk-lib/aws-lambda';
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from 'aws-cdk-lib/aws-ec2';

import { Construct } from 'constructs';
import { join } from "path";

interface apiStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
}

export class LLMApiStack extends NestedStack {

    constructor(scope: Construct, id: string, props: apiStackProps) {
        super(scope, id, props);

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint

        const lambdaExecutor = new DockerImageFunction(this,
            "lambdaExecutor", {
            code: DockerImageCode.fromImageAsset(join(__dirname, "../src/lambda/executor")),
            timeout: Duration.minutes(15),
            memorySize: 1024,
            vpc: _vpc,
            vpcSubnets: {
                subnets: _vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            architecture: Architecture.X86_64,
            environment: {
              aos_endpoint: _domainEndpoint,
            },
          });

        lambdaExecutor.addToRolePolicy(new iam.PolicyStatement({
        // principals: [new iam.AnyPrincipal()],
            actions: [ 
            "sagemaker:InvokeEndpointAsync",
            "sagemaker:InvokeEndpoint",
            "s3:List*",
            "s3:Put*",
            "s3:Get*",
            "es:*",
            "dynamodb:*",
            "secretsmanager:GetSecretValue",
            ],
            effect: iam.Effect.ALLOW,
            resources: ['*'],
            }
        ))

    }
}