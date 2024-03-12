/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

// Reference: https://github.com/awslabs/sensitive-data-protection-on-aws/blob/main/source/constructs/lib/common/build-config.ts
export class BuildConfig {
    // There are three mode for deployment: OFFLINE_EXTRACT, OFFLINE_OPENSEARCH, ALL
    static DEPLOYMENT_MODE = 'ALL';
    static LAYER_PIP_OPTION = '';
    static JOB_PIP_OPTION = '';
    static LLM_MODEL_ID = '';
    static LLM_ENDPOINT_NAME = '';
  }