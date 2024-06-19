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

import { CfnParameter } from "aws-cdk-lib";
import { Construct } from "constructs";

interface CdkParameters {
  s3ModelAssets: CfnParameter;
  subEmail: CfnParameter;
  openSearchIndex: CfnParameter;
  etlImageTag: CfnParameter;
  openSearchIndexDict: CfnParameter;
  etlImageName: CfnParameter;
}

export class DeploymentParameters implements CdkParameters {
  public stackName: CfnParameter;
  public s3ModelAssets: CfnParameter;
  public subEmail: CfnParameter;
  public openSearchIndex: CfnParameter;
  public etlImageTag: CfnParameter;
  public openSearchIndexDict: CfnParameter;
  public etlImageName: CfnParameter;

  constructor(scope: Construct) {

    this.stackName = new CfnParameter(scope, 'StackName', {
      type: 'String',
      description: 'The name of the stack',
      default: 'intelli-agent',
    });

    this.s3ModelAssets = new CfnParameter(scope, "S3ModelAssets", {
      type: "String",
      description: "S3 Bucket for model & code assets",
    });

    this.subEmail = new CfnParameter(scope, "SubEmail", {
      type: "String",
      description: "Email address for SNS notification",
    });

    this.openSearchIndex = new CfnParameter(scope, "OpenSearchIndex", {
      type: "String",
      description: "OpenSearch index to store knowledge",
      default: "chatbot-index",
    });

    this.etlImageTag = new CfnParameter(scope, "ETLTag", {
      type: "String",
      description: "ETL image tag, the default is latest",
      default: "latest",
    });

    let OpenSearchIndexDictDefaultValue: string | undefined;

    if (process.env.AOSDictValue !== undefined) {
      OpenSearchIndexDictDefaultValue = process.env.AOSDictValue;
    } else {
      OpenSearchIndexDictDefaultValue =
        '{"aos_index_mkt_qd":"aws-cn-mkt-knowledge","aos_index_mkt_qq":"gcr-mkt-qq","aos_index_dgr_qd":"ug-index-20240108","aos_index_dgr_qq":"gcr-dgr-qq", "aos_index_dgr_faq_qd":"faq-index-20240110", "dummpy_key":"dummpy_value"}';
    }

    this.openSearchIndexDict = new CfnParameter(scope, "OpenSearchIndexDict", {
      type: "String",
      description: "OpenSearch index to store knowledge dict format",
      default: OpenSearchIndexDictDefaultValue,
    });

    this.etlImageName = new CfnParameter(scope, "EtlImageName", {
      type: "String",
      description: "The ECR image name which is used for ETL, eg. etl-model",
    });
  }
}
