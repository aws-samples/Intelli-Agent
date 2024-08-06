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
        // Set * to deny all HTTP request for security
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
