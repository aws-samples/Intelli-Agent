import { NestedStack, RemovalPolicy, StackProps } from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import { Domain, EngineVersion } from "aws-cdk-lib/aws-opensearchservice";
import { Construct } from "constructs";

import { BuildConfig } from "../../lib/shared/build-config";

interface OSStackProps extends StackProps {
  osVpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
}

export class OpenSearchStack extends NestedStack {
  public domainEndpoint;
  public domain;

  constructor(scope: Construct, id: string, props: OSStackProps) {
    super(scope, id, props);
    console.log("BuildConfig.DEPLOYMENT_MODE: ", BuildConfig.DEPLOYMENT_MODE);

    // If deplyment mode is OFFLINE_OPENSEARCH or ALL, then create the following resources
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
