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

import { Aws, Duration, StackProps } from "aws-cdk-lib";
import { Function, Runtime, Code, Architecture, FunctionProps } from 'aws-cdk-lib/aws-lambda';
import { Construct } from "constructs";
import { IVpc, SecurityGroup } from "aws-cdk-lib/aws-ec2";
import { ILayerVersion } from "aws-cdk-lib/aws-lambda";
import { Role, PolicyStatement } from "aws-cdk-lib/aws-iam";


interface LambdaFunctionProps {
  runtime?: Runtime;
  handler?: string;
  code: Code;
  vpc?: IVpc;
  securityGroups?: [SecurityGroup];
  environment?: { [key: string]: string };
  layers?: ILayerVersion[];
  memorySize?: number;
  role?: Role;
  statements?: PolicyStatement[];
}

export class LambdaFunction extends Construct {
  public function: Function;

  constructor(scope: Construct, name: string, props: LambdaFunctionProps) {
    super(scope, name);

    const defaultRuntime = Runtime.PYTHON_3_12;
    const defaultHandler = "main.lambda_handler";

    let functionProps: FunctionProps = {
      runtime: props.runtime ?? defaultRuntime,
      handler: props.handler ?? defaultHandler,
      code: props.code,
      timeout: Duration.minutes(15),
      memorySize: props.memorySize ?? 1024,
      environment: props.environment,
      layers: props.layers,
    };

    if (props.vpc) {
      functionProps = {
        ...functionProps,
        vpc: props.vpc,
        vpcSubnets: {
          subnets: props.vpc.privateSubnets,
        }
      };
    }
    if (props.securityGroups) {
      functionProps = {
        ...functionProps,
        securityGroups: props.securityGroups,
      };
    }
    if (props.role) {
      functionProps = {
        ...functionProps,
        role: props.role,
      };
    }

    this.function = new Function(this, name, functionProps);

    // Iterate through all the statements and add them to the Lambda function
    props.statements?.forEach((statement) => {
      this.function.addToRolePolicy(statement);
    });
  }
}