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

import { Aws } from "aws-cdk-lib";
import { Construct } from "constructs";
import {PolicyStatement, Effect} from "aws-cdk-lib/aws-iam";

export class IAMHelper extends Construct {
  public logStatement: PolicyStatement;
  public s3Statement: PolicyStatement;
  public glueStatement: PolicyStatement;
  public endpointStatement: PolicyStatement;
  public dynamodbStatement: PolicyStatement;

  public createPolicyStatement(actions: string[], resources: string[]) {
    return new PolicyStatement({
      effect: Effect.ALLOW,
      actions: actions,
      resources: resources,
    });
  }

  constructor(scope: Construct, name: string) {
    super(scope, name);

    // Common IAM policy statement
    this.logStatement = this.createPolicyStatement(
      [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ],
      [ `arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*` ],
    );
    this.s3Statement = this.createPolicyStatement(
      [
        "s3:Get*",
        "s3:List*",
        "s3:PutObject",
        "s3:GetObject",
      ],
      [ "*" ],
    );
    this.glueStatement = this.createPolicyStatement(
      [
        "glue:StartJobRun",
        "glue:GetJobRun*",
      ],
      [ "*" ],
    );
    this.endpointStatement = this.createPolicyStatement(
      [
        "sagemaker:InvokeEndpointAsync",
        "sagemaker:InvokeEndpoint",
      ],
      [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`],
    );
    this.dynamodbStatement = this.createPolicyStatement(
        [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Describe*",
          "dynamodb:List*",
          "dynamodb:Scan",
        ],
        [`arn:${Aws.PARTITION}:dynamodb:${Aws.REGION}:${Aws.ACCOUNT_ID}:table/*`],
      );
  }
}
