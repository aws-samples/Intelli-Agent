import { StackProps, Duration } from "aws-cdk-lib";
import { Queue, QueueEncryption } from "aws-cdk-lib/aws-sqs";
import { AnyPrincipal, Effect, PolicyStatement } from "aws-cdk-lib/aws-iam";
import { Function } from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";
import { Rule } from "aws-cdk-lib/aws-events";
import { LambdaFunction } from "aws-cdk-lib/aws-events-targets";

export interface ConnectProps extends StackProps {
  readonly lambdaOnlineMain: Function;
}

export class ConnectConstruct extends Construct {
  constructor(scope: Construct, id: string, props: ConnectProps) {
    super(scope, id);

    const dlq = new Queue(this, "ConnectDLQ", {
      encryption: QueueEncryption.KMS_MANAGED,
      retentionPeriod: Duration.days(14),
      visibilityTimeout: Duration.hours(10),
    });

    const messageQueue = new Queue(this, "ConnectMessageQueue", {
      encryption: QueueEncryption.KMS_MANAGED,
      visibilityTimeout: Duration.hours(3),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 50,
      },
    });

    messageQueue.addToResourcePolicy(
      new PolicyStatement({
        effect: Effect.DENY,
        principals: [new AnyPrincipal()],
        actions: ["sqs:*"],
        resources: ["*"],
        conditions: {
          Bool: { "aws:SecureTransport": "false" }
        }
      })
    );

    const connectRule = new Rule(
      this,
      "ConnectRule",
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

    const eventLambdaFunction = new LambdaFunction(props.lambdaOnlineMain);
    connectRule.addTarget(eventLambdaFunction);
  }
}
