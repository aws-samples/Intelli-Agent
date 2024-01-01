import { NestedStack, StackProps, } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as batch from 'aws-cdk-lib/aws-batch';

interface connectorStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
    _embeddingEndPoints: string[];
    _OpenSearchIndex: string;
    _OpenSearchIndexDict: string;
}

export class ConnectorStack extends NestedStack {

    _jobQueueArn: string;
    _jobDefinitionName: string;

    constructor(scope: Construct, id: string, props: connectorStackProps) {
        super(scope, id, props);

        const _vpc = props._vpc
        const _securityGroup = props._securityGroup
        const _domainEndpoint = props._domainEndpoint
        const _embeddingEndPoints = props._embeddingEndPoints
        const _aosIndex = props._OpenSearchIndex
        const _aosIndexDict = props._OpenSearchIndexDict

        // Define VPC, this VPC should be the same as RDS instance specified by user, otherwise, the lambda function cannot access RDS
        // We use the same VPC as solution to create the stack for now
        const vpc = _vpc
        
        // Define batch compute environment with fargate
        const compEnv = new batch.CfnComputeEnvironment(this, 'ComputeEnvironment', {
            type: 'MANAGED',
            computeEnvironmentName: 'fargate-compute-environment',
            computeResources: {
                type: 'FARGATE',
                // Not support in faragte
                // minvCpus: 0,
                maxvCpus: 256,
                // desiredvCpus: 0,
                // instanceTypes: ['optimal'],
                subnets: vpc.privateSubnets.map(subnet => subnet.subnetId),
                securityGroupIds: [_securityGroup.securityGroupId],
                // tags: {
                //     Name: 'fargate-compute-environment'
                // }
            }
        })

        // Define the batch job queue
        const jobQueue = new batch.CfnJobQueue(this, 'JobQueue', {
            jobQueueName: 'fargate-job-queue',
            priority: 1,
            computeEnvironmentOrder: [{
                order: 1,
                computeEnvironment: compEnv.ref
            }]
        })

        // Define a job definition
        const jobDefinition = new batch.CfnJobDefinition(this, 'JobDefinition', {
            jobDefinitionName: 'fargate-job-definition',
            type: 'container',
            containerProperties: {
                // using public ecr image as placeholder for now
                image: 'public.ecr.aws/lambda/python:3.10',
                vcpus: 1,
                memory: 2048,
                command: ['python', 'main.py'],
                environment: (
                    [
                        {
                            name: 'DOMAIN_ENDPOINT',
                            value: _domainEndpoint
                        },
                        {
                            name: 'EMBEDDING_ENDPOINTS',
                            value: _embeddingEndPoints.join(',')
                        },
                        {
                            name: 'AOS_INDEX',
                            value: _aosIndex
                        },
                        {
                            name: 'AOS_INDEX_DICT',
                            value: _aosIndexDict
                        },
                        // RDS instance, user and password will be pass from lambda function using environment variables
                    ]
                ),
            }
        })

        this._jobQueueArn = jobQueue.attrJobQueueArn;
        this._jobDefinitionName = jobDefinition.jobDefinitionName!;
    }
}