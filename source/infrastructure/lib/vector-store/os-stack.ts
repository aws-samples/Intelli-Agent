import { NestedStack, StackProps, RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { EngineVersion, Domain} from 'aws-cdk-lib/aws-opensearchservice';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from "aws-cdk-lib/aws-iam";

interface osStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
}

export class OpenSearchStack extends NestedStack {
    _domainEndpoint;
    _domain;

    constructor(scope: Construct, id: string, props: osStackProps) {
        super(scope, id, props);

        const devDomain = new Domain(this, 'Domain', {
            version: EngineVersion.OPENSEARCH_2_5,
            removalPolicy: RemovalPolicy.DESTROY,
            vpc:props._vpc,
            zoneAwareness: {
            enabled:true
            },
            securityGroups: [props._securityGroup],
            capacity: {
                dataNodes: 2,
            },
            ebs: {
                volumeSize: 300,
                volumeType: ec2.EbsDeviceVolumeType.GENERAL_PURPOSE_SSD_GP3,
            },
        });

        devDomain.addAccessPolicies(new iam.PolicyStatement({
            actions: ['es:*'],
            effect: iam.Effect.ALLOW,
            principals:[new iam.AnyPrincipal()],
            resources: [`${devDomain.domainArn}/*`],
        }))

        this._domainEndpoint = devDomain.domainEndpoint;
        this._domain = devDomain;

    }
}