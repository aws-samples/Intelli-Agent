import { NestedStack, StackProps, Size } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as batch from 'aws-cdk-lib/aws-batch';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';

interface connectorStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
    _embeddingEndPoints: string[];
    _OpenSearchIndex: string;
    _OpenSearchIndexDict: string;
}

export class ConnectorStack extends NestedStack {

    _jobName: string;
    _jobQueueArn: string;
    _jobDefinitionArn: string;

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
        const computeEnvironment = new batch.FargateComputeEnvironment(this, 'ComputeEnvironment', {
            computeEnvironmentName: 'batch-compute-environment',
            vpc: vpc,
            vpcSubnets: {
                subnets: vpc.privateSubnets,
            },
            securityGroups: [_securityGroup],
            maxvCpus: 256,
            spot: false,
        });

        // Define job queue
        const jobQueue = new batch.JobQueue(this, 'JobQueue', {
            jobQueueName: 'batch-job-queue',
            computeEnvironments: [{
                computeEnvironment: computeEnvironment,
                order: 1,
            }],
        });

        // Define job definition
        const jobDefinition = new batch.EcsJobDefinition(this, 'JobDefn', {
            container: new batch.EcsFargateContainerDefinition(this, 'containerDefn', {
                image: ecs.ContainerImage.fromAsset('./lib/connector/image'),
                memory: Size.mebibytes(2048),
                cpu: 1,
                environment: {
                    DOMAIN_ENDPOINT: _domainEndpoint,
                    EMBEDDING_ENDPOINTS: _embeddingEndPoints.join(','),
                    AOS_INDEX: _aosIndex,
                    AOS_INDEX_DICT: _aosIndexDict
                },
            }),
            jobDefinitionName: 'batch-job-definition',
        });

        this._jobName = jobDefinition.jobDefinitionName;
        this._jobQueueArn = jobQueue.jobQueueArn;
        this._jobDefinitionArn = jobDefinition.jobDefinitionArn;
    }
}