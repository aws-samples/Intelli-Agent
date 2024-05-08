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

import { NestedStack, StackProps, Size } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as batch from "aws-cdk-lib/aws-batch";
import * as ecs from "aws-cdk-lib/aws-ecs";

interface connectorStackProps extends StackProps {
  connectorVpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
  domainEndpoint: string;
  embeddingEndPoints: string[];
  openSearchIndex: string;
  openSearchIndexDict: string;
}

export class ConnectorConstruct extends Construct {
  public jobName: string;
  public jobQueueArn: string;
  public jobDefinitionArn: string;

  constructor(scope: Construct, id: string, props: connectorStackProps) {
    super(scope, id);

    const connectorVpc = props.connectorVpc;
    const securityGroup = props.securityGroup;
    const domainEndpoint = props.domainEndpoint;
    const embeddingEndPoints = props.embeddingEndPoints;
    const aosIndex = props.openSearchIndex;
    const aosIndexDict = props.openSearchIndexDict;

    // Define batch compute environment with fargate
    const computeEnvironment = new batch.FargateComputeEnvironment(
      this,
      "ComputeEnvironment",
      {
        computeEnvironmentName: "batch-compute-environment",
        vpc: connectorVpc,
        vpcSubnets: {
          subnets: connectorVpc.privateSubnets,
        },
        securityGroups: [securityGroup],
        maxvCpus: 256,
        spot: false,
      },
    );

    // Define job queue
    const jobQueue = new batch.JobQueue(this, "JobQueue", {
      jobQueueName: "batch-job-queue",
      computeEnvironments: [
        {
          computeEnvironment: computeEnvironment,
          order: 1,
        },
      ],
    });

    // Define job definition
    const jobDefinition = new batch.EcsJobDefinition(this, "JobDefn", {
      container: new batch.EcsFargateContainerDefinition(
        this,
        "containerDefn",
        {
          image: ecs.ContainerImage.fromAsset("./lib/connector/image"),
          memory: Size.mebibytes(2048),
          cpu: 1,
          environment: {
            DOMAIN_ENDPOINT: domainEndpoint,
            EMBEDDING_ENDPOINTS: embeddingEndPoints.join(","),
            AOS_INDEX: aosIndex,
            AOS_INDEX_DICT: aosIndexDict,
          },
        },
      ),
      jobDefinitionName: "batch-job-definition",
    });

    this.jobName = jobDefinition.jobDefinitionName;
    this.jobQueueArn = jobQueue.jobQueueArn;
    this.jobDefinitionArn = jobDefinition.jobDefinitionArn;
  }
}
