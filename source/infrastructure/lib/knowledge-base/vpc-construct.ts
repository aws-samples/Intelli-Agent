/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";
import * as dotenv from "dotenv";

dotenv.config();

export class VpcConstruct extends Construct {
  public connectorVpc;
  public privateSubnets;
  public securityGroup;

  constructor(scope: Construct, id: string) {
    super(scope, id);

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
