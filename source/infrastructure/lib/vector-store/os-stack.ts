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

import { BuildConfig } from "../../lib/shared/build-config";

interface AOSProps extends StackProps {
  osVpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
}

export class AOSConstruct extends Construct {
  public domainEndpoint;
  public domain;

  constructor(scope: Construct, id: string, props: AOSProps) {
    super(scope, id);
    console.log("BuildConfig.DEPLOYMENT_MODE: ", BuildConfig.DEPLOYMENT_MODE);

    // If deployment mode is OFFLINE_OPENSEARCH or ALL, then create the following resources
    if (
      BuildConfig.DEPLOYMENT_MODE === "OFFLINE_OPENSEARCH" ||
      BuildConfig.DEPLOYMENT_MODE === "ALL"
    ) {
      const devDomain = new Domain(this, "Domain", {
        version: EngineVersion.OPENSEARCH_2_5,
        removalPolicy: RemovalPolicy.DESTROY,
        vpc: props.osVpc,
        zoneAwareness: {
          enabled: true,
        },
        securityGroups: [props.securityGroup],
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
      this.domain = devDomain;
    }
  }
}
