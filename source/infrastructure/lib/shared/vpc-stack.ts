import { NestedStack, StackProps }  from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as ec2 from 'aws-cdk-lib/aws-ec2';

import * as dotenv from "dotenv";
dotenv.config();

export class VpcStack extends NestedStack {
  
  _vpc;
  _privateSubnets;
  _securityGroup;

  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    this._vpc = new ec2.Vpc(this, 'LLM-VPC', {
      ipAddresses: ec2.IpAddresses.cidr('10.100.0.0/16'),
      maxAzs: 2,
    });

    this._privateSubnets = this._vpc.privateSubnets;

    this._securityGroup = new ec2.SecurityGroup(this, 'LLM-VPC-SG', {
      vpc: this._vpc,
      description: 'LLM Security Group'
    });

    this._securityGroup.addIngressRule(this._securityGroup, ec2.Port.allTraffic(), 'allow self traffic');

    this._vpc.addGatewayEndpoint('DynamoDbEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
    });

    this._vpc.addInterfaceEndpoint('Glue', {
      service: ec2.InterfaceVpcEndpointAwsService.GLUE,
      securityGroups: [this._securityGroup],
      subnets: { subnets: this._privateSubnets, },
    });

  }
}