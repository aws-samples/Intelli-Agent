
import { NestedStack, StackProps }  from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import { Asset } from 'aws-cdk-lib/aws-s3-assets';

import path from "path";

interface Ec2StackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
}

export class Ec2Stack extends NestedStack {
    _instanceId;
    _dnsName;
    _publicIP;

    constructor(scope: Construct, id: string, props: Ec2StackProps) {
      super(scope, id, props);
        const _vpc = props._vpc;
        const _securityGroup = props._securityGroup;
        const _domainEndpoint = props._domainEndpoint;

        _securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22), 'Allow SSH Access')
        _securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow HTTPS Access')
        _securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8081), 'Allow HTTP 8081 port Access')
        _securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP Access')
        _securityGroup.addIngressRule(_securityGroup, ec2.Port.allTraffic(), 'Allow Self Access')

        const role = new iam.Role(this, 'ec2Role', {
            assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com')
        })
        
        role.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'))
    
        const ami = new ec2.AmazonLinuxImage({
        generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
        cpuType: ec2.AmazonLinuxCpuType.X86_64
        });
    
        // Create the instance using the Security Group, AMI, and KeyPair defined in the VPC created
        const ec2Instance = new ec2.Instance(this, 'ProxyInstance', {
          vpc: _vpc,
          instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
          machineImage: ami,
          securityGroup: _securityGroup,
          vpcSubnets: {subnetType: ec2.SubnetType.PUBLIC,},
          // specify the key name for the instance for debugging purposes
          // keyName: 'us-east-1',
        });

        const asset = new Asset(this, 'UserdataAsset', { path: path.join(__dirname, '../script/ec2config.sh') });
        const localPath = ec2Instance.userData.addS3DownloadCommand({
          bucket: asset.bucket,
          bucketKey: asset.s3ObjectKey,
        });
    
        ec2Instance.userData.addExecuteFileCommand({
          filePath: localPath,
          // pass _domainEndpoint as an argument to the script
          arguments: _domainEndpoint,
        });
        asset.grantRead(ec2Instance.role);

        this._instanceId = ec2Instance.instanceId;
        this._dnsName = ec2Instance.instancePublicDnsName;
        this._publicIP = ec2Instance.instancePublicIp;
    }
  }