import { Duration, StackProps } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

export interface QueueProps extends StackProps {
  namePrefix: string;
}

export class QueueConstruct extends Construct {
  public readonly sqsStatement: iam.PolicyStatement;
  public readonly messageQueue: sqs.Queue;
  public readonly dlq: sqs.Queue;

  constructor(scope: Construct, id: string, props: QueueProps) {
    super(scope, id);

    const dlq = new sqs.Queue(this, `${props.namePrefix}DLQ`, {
      encryption: sqs.QueueEncryption.KMS_MANAGED,
      retentionPeriod: Duration.days(14),
      visibilityTimeout: Duration.hours(10),
    });

    const messageQueue = new sqs.Queue(this, `${props.namePrefix}Queue`, {
      encryption: sqs.QueueEncryption.KMS_MANAGED,
      visibilityTimeout: Duration.hours(3),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 50,
      },
    });
    messageQueue.addToResourcePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.DENY,
        principals: [new iam.AnyPrincipal()],
        actions: ["sqs:*"],
        resources: ["*"],
        conditions: {
          Bool: { "aws:SecureTransport": "false" },
        },
      }),
    );

    const sqsStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      resources: [messageQueue.queueArn],
      actions: [
        "sqs:DeleteMessage",
        "sqs:GetQueueUrl",
        "sqs:ChangeMessageVisibility",
        "sqs:PurgeQueue",
        "sqs:ReceiveMessage",
        "sqs:SendMessage",
        "sqs:GetQueueAttributes",
        "sqs:SetQueueAttributes",
      ],
    });

    this.sqsStatement = sqsStatement;
    this.messageQueue = messageQueue;
    this.dlq = dlq;
  }
}
