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

import { RemovalPolicy, StackProps } from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import { Domain, EngineVersion } from "aws-cdk-lib/aws-opensearchservice";
import { Construct } from "constructs";

interface AOSProps extends StackProps {
  osVpc?: ec2.Vpc;
  securityGroup?: [ec2.SecurityGroup];
  useCustomDomain: boolean;
  customDomainEndpoint: string;
}

export class AOSConstruct extends Construct {
  public domainEndpoint;

  constructor(scope: Construct, id: string, props: AOSProps) {
    super(scope, id);

    if (props.useCustomDomain) {
      const devDomain = Domain.fromDomainEndpoint(this, "Domain", props.customDomainEndpoint);
      this.domainEndpoint = devDomain.domainEndpoint;
    } else {

      const devDomain = new Domain(this, "Domain", {
        version: EngineVersion.OPENSEARCH_2_17,
        removalPolicy: RemovalPolicy.DESTROY,
        vpc: props.osVpc,
        zoneAwareness: {
          enabled: true,
        },
        securityGroups: props.securityGroup,
        capacity: {
          dataNodes: 2,
          dataNodeInstanceType: "r6g.2xlarge.search",
        },
        ebs: {
          volumeSize: 300,
          volumeType: ec2.EbsDeviceVolumeType.GENERAL_PURPOSE_SSD_GP3,
        },
      });

      devDomain.addAccessPolicies(
        new iam.PolicyStatement({
          actions: ["es:*"],
          effect: iam.Effect.ALLOW,
          principals: [new iam.AnyPrincipal()],
          resources: [`${devDomain.domainArn}/*`],
        }),
      );

      this.domainEndpoint = devDomain.domainEndpoint;
    }

  }
}
