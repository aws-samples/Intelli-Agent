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
  public embeddingAndRerankerModelPrefix;
  public embeddingAndRerankerModelVersion;
  public instructModelPrefix;
  public instructModelVersion;
  public etlCodePrefix;
  public s3ModelAssets: string;

  constructor(scope: Construct, id: string, props: AssetsStackProps) {
    super(scope, id);

    const embeddingAndRerankerModelPrefix = "bce-embedding-and-bge-reranker";
    const embeddingAndRerankerModelVersion = "43972580a35ceacacd31b95b9f430f695d07dde9";
    const instructModelPrefix = "internlm2-chat-20b";
    const instructModelVersion = "7bae8edab7cf91371e62506847f2e7fdc24c6a65";
    const etlCodePrefix = "buffer_etl_deploy_code";

    this.embeddingAndRerankerModelPrefix = embeddingAndRerankerModelPrefix;
    this.embeddingAndRerankerModelVersion = embeddingAndRerankerModelVersion;
    this.instructModelPrefix = instructModelPrefix;
    this.instructModelVersion = instructModelVersion;
    this.etlCodePrefix = etlCodePrefix;
    this.s3ModelAssets = props.s3ModelAssets;
  }
}
