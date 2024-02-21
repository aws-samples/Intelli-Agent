import { NestedStack, StackProps, RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { EngineVersion, Domain } from 'aws-cdk-lib/aws-opensearchservice';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from "aws-cdk-lib/aws-iam";
import { BuildConfig } from '../../lib/shared/build-config';

interface osStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
}

export class OpenSearchStack extends NestedStack {
    _domainEndpoint;
    _domain;

    constructor(scope: Construct, id: string, props: osStackProps) {
        super(scope, id, props);
        console.log('BuildConfig.DEPLOYMENT_MODE: ', BuildConfig.DEPLOYMENT_MODE);

        // If Deplyment mode is OFFLINE_OPENSEARCH or ALL, then create the following resources
        if (BuildConfig.DEPLOYMENT_MODE === 'OFFLINE_OPENSEARCH' || BuildConfig.DEPLOYMENT_MODE === 'ALL') {

            const devDomain = new Domain(this, 'Domain', {
                version: EngineVersion.OPENSEARCH_2_5,
                removalPolicy: RemovalPolicy.DESTROY,
                vpc: props._vpc,
                zoneAwareness: {
                    enabled: true
                },
                securityGroups: [props._securityGroup],
                capacity: {
                    // 2 * c6g.4xlarge DataNode, 3 * m6g.large MasterNode
                    dataNodes: 2,
                    dataNodeInstanceType: 'r6g.2xlarge.search',
                    // masterNodes: 3,
                    // masterNodeInstanceType: 'm6g.2xlarge.search',
                },
                ebs: {
                    volumeSize: 300,
                    volumeType: ec2.EbsDeviceVolumeType.GENERAL_PURPOSE_SSD_GP3,
                },
            });

            devDomain.addAccessPolicies(new iam.PolicyStatement({
                actions: ['es:*'],
                effect: iam.Effect.ALLOW,
                principals: [new iam.AnyPrincipal()],
                resources: [`${devDomain.domainArn}/*`],
            }))

            this._domainEndpoint = devDomain.domainEndpoint;
            this._domain = devDomain;
        }


    }
}