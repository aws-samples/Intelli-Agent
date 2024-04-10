import { NestedStack, StackProps } from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";
import * as dotenv from "dotenv";

dotenv.config();

export class VpcStack extends NestedStack {
  public connectorVpc;
  public privateSubnets;
  public securityGroup;

  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    this.connectorVpc = new ec2.Vpc(this, "LLM-VPC", {
      ipAddresses: ec2.IpAddresses.cidr("10.100.0.0/16"),
      maxAzs: 2,
    });

    this.privateSubnets = this.connectorVpc.privateSubnets;

    this.securityGroup = new ec2.SecurityGroup(this, "LLM-VPC-SG", {
      vpc: this.connectorVpc,
      description: "LLM Security Group",
    });

    this.securityGroup.addIngressRule(
      this.securityGroup,
      ec2.Port.allTraffic(),
      "allow self traffic",
    );

    this.connectorVpc.addGatewayEndpoint("DynamoDbEndpoint", {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
    });

    this.connectorVpc.addInterfaceEndpoint("Glue", {
      service: ec2.InterfaceVpcEndpointAwsService.GLUE,
      securityGroups: [this.securityGroup],
      subnets: { subnets: this.privateSubnets },
    });
  }
}
