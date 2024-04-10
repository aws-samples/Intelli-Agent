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

export class ConnectorStack extends NestedStack {
  public jobName: string;
  public jobQueueArn: string;
  public jobDefinitionArn: string;

  constructor(scope: Construct, id: string, props: connectorStackProps) {
    super(scope, id, props);

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
