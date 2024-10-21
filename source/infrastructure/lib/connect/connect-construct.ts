import { StackProps, Duration, NestedStack } from "aws-cdk-lib";
import { Queue, QueueEncryption } from "aws-cdk-lib/aws-sqs";
import { AnyPrincipal, Effect, PolicyStatement } from "aws-cdk-lib/aws-iam";
import { Function } from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";
import { Rule } from "aws-cdk-lib/aws-events";
import { LambdaFunction, SqsQueue } from "aws-cdk-lib/aws-events-targets";
import { SqsEventSource } from "aws-cdk-lib/aws-lambda-event-sources";

export interface ConnectProps extends StackProps {
  readonly lambdaOnlineMain: Function;
}

export class ConnectConstruct extends NestedStack {
  constructor(scope: Construct, id: string, props: ConnectProps) {
    super(scope, id);

    const dlq = new Queue(this, "ConnectDLQ", {
      encryption: QueueEncryption.SQS_MANAGED,
      retentionPeriod: Duration.days(14),
      visibilityTimeout: Duration.hours(10),
    });

    const messageQueue = new Queue(this, "ConnectMessageQueue", {
      encryption: QueueEncryption.SQS_MANAGED,
      visibilityTimeout: Duration.hours(3),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 50,
      },
    });

    const connectRule = new Rule(
      this,
      "CaseRule",
      {
        eventPattern: {
          source: ["aws.cases"],
          detail: {
            eventType: [
              "RELATED_ITEM.CREATED",
            ],
          },
        },
      }
    );

    connectRule.addTarget(new SqsQueue(messageQueue));
    props.lambdaOnlineMain.addEventSource(
      new SqsEventSource(messageQueue, { batchSize: 10 }),
    );
  }
}
