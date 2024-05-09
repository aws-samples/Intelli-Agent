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

import { StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dotenv from "dotenv";

dotenv.config();

interface AssetsStackProps extends StackProps {
  s3ModelAssets: string;
}

export class AssetsConstruct extends Construct {
  public rerankModelPrefix;
  public rerankModelVersion;
  public embeddingModelPrefix;
  public embeddingModelVersion;
  public instructModelPrefix;
  public instructModelVersion;
  public etlCodePrefix;
  public s3ModelAssets: string;

  constructor(scope: Construct, id: string, props: AssetsStackProps) {
    super(scope, id);

    const rerankModelPrefix = "bge-reranker-large";
    const rerankModelVersion = "27c9168d479987529781de8474dff94d69beca11";
    const embeddingModelPrefix: string[] = ["bge-m3"];
    const embeddingModelVersion: string[] = [
      "3ab7155aa9b89ac532b2f2efcc3f136766b91025",
    ];
    const instructModelPrefix = "internlm2-chat-20b";
    const instructModelVersion = "7bae8edab7cf91371e62506847f2e7fdc24c6a65";
    const etlCodePrefix = "buffer_etl_deploy_code";

    this.rerankModelPrefix = rerankModelPrefix;
    this.rerankModelVersion = rerankModelVersion;
    this.embeddingModelPrefix = embeddingModelPrefix;
    this.embeddingModelVersion = embeddingModelVersion;
    this.instructModelPrefix = instructModelPrefix;
    this.instructModelVersion = instructModelVersion;
    this.etlCodePrefix = etlCodePrefix;
    this.s3ModelAssets = props.s3ModelAssets;
  }
}
