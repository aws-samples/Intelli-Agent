import { App, CfnOutput, CfnParameter, Stack, StackProps } from 'aws-cdk-lib';
import {Runtime, Code, LayerVersion} from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';
import { Construct } from 'constructs';
import * as dotenv from "dotenv";
import { LLMApiStack } from '../lib/api/api-stack';
import { DynamoDBStack } from '../lib/ddb/ddb-stack';
import { EtlStack } from '../lib/etl/etl-stack';
import { AssetsStack } from '../lib/model/assets-stack';
import { LLMStack } from '../lib/model/llm-stack';
import { BuildConfig } from '../lib/shared/build-config';
import { DeploymentParameters } from '../lib/shared/cdk-parameters';
import { VpcStack } from '../lib/shared/vpc-stack';
import { OpenSearchStack } from '../lib/vector-store/os-stack';

dotenv.config();

export class RootStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    this.setBuildConfig();

    const _CdkParameters = new DeploymentParameters(this);

    const _AssetsStack = new AssetsStack(this, 'assets-stack', { _s3ModelAssets: _CdkParameters._S3ModelAssets.valueAsString, env: process.env });
    const _LLMStack = new LLMStack(this, 'llm-stack', {
      _s3ModelAssets: _CdkParameters._S3ModelAssets.valueAsString,
      _rerankModelPrefix: _AssetsStack._rerankModelPrefix,
      _rerankModelVersion: _AssetsStack._rerankModelVersion,
      _embeddingModelPrefix: _AssetsStack._embeddingModelPrefix,
      _embeddingModelVersion: _AssetsStack._embeddingModelVersion,
      _instructModelPrefix: _AssetsStack._instructModelPrefix,
      _instructModelVersion: _AssetsStack._instructModelVersion,
      env: process.env
    });
    _LLMStack.addDependency(_AssetsStack);

    const _VpcStack = new VpcStack(this, 'vpc-stack', { env: process.env });


    const _OsStack = new OpenSearchStack(this, 'os-stack', { _vpc: _VpcStack._vpc, _securityGroup: _VpcStack._securityGroup });
    _OsStack.addDependency(_VpcStack);

    const _DynamoDBStack = new DynamoDBStack(this, 'ddb-stack', { _vpc: _VpcStack._vpc, _securityGroup: _VpcStack._securityGroup, env: process.env });
    _DynamoDBStack.addDependency(_VpcStack);

    const _EtlStack = new EtlStack(this, 'etl-stack', {
      _domainEndpoint: _OsStack._domainEndpoint || '',
      _embeddingEndpoint: _LLMStack._embeddingEndPoints,
      _region: props.env?.region || 'us-east-1',
      _subEmail: _CdkParameters._SubEmail.valueAsString ?? '',
      _vpc: _VpcStack._vpc,
      _subnets: _VpcStack._privateSubnets,
      _securityGroups: _VpcStack._securityGroup,
      _s3ModelAssets: _CdkParameters._S3ModelAssets.valueAsString,
      _OpenSearchIndex: _CdkParameters._OpenSearchIndex.valueAsString,
    });
    _EtlStack.addDependency(_VpcStack);
    _EtlStack.addDependency(_OsStack);
    _EtlStack.addDependency(_LLMStack);
    
    const _ApiStack = new LLMApiStack(this, 'api-stack', {
      _vpc:_VpcStack._vpc,
      _securityGroup:_VpcStack._securityGroup,
      _domainEndpoint:_OsStack._domainEndpoint || '',
      _rerankEndPoint: _LLMStack._rerankEndPoint ?? '',
      _embeddingEndPoints:_LLMStack._embeddingEndPoints || '',
      _instructEndPoint:_LLMStack._instructEndPoint || '',
      _chatSessionTable: _DynamoDBStack._chatSessionTable,
      _sfnOutput: _EtlStack._sfnOutput,
      _OpenSearchIndex: _CdkParameters._OpenSearchIndex.valueAsString,
      _OpenSearchIndexDict: _CdkParameters._OpenSearchIndexDict.valueAsString,
      _etlEndpoint: _EtlStack._etlEndpoint,
      _resBucketName: _EtlStack._resBucketName,
      env: process.env
    });
    _ApiStack.addDependency(_VpcStack);
    _ApiStack.addDependency(_OsStack);
    _ApiStack.addDependency(_LLMStack);
    _ApiStack.addDependency(_DynamoDBStack);
    _ApiStack.addDependency(_DynamoDBStack);
    _ApiStack.addDependency(_EtlStack);

    new CfnOutput(this, 'VPC', {value:_VpcStack._vpc.vpcId});
    new CfnOutput(this, 'OpenSearch Endpoint', {value:_OsStack._domainEndpoint || 'No OpenSearch Endpoint Created'});
    new CfnOutput(this, 'Document Bucket', {value:_ApiStack._documentBucket});
    // deprecate for now since proxy in ec2 instance is not allowed according to policy
    // new CfnOutput(this, 'OpenSearch Dashboard', {value:`${_Ec2Stack._publicIP}:8081/_dashboards`});
    new CfnOutput(this, 'API Endpoint Address', {value:_ApiStack._apiEndpoint});
    new CfnOutput(this, 'WebSocket Endpoint Address', {value:_ApiStack._wsEndpoint});
    new CfnOutput(this, 'Glue Job Name', {value:_EtlStack._jobName});
    new CfnOutput(this, 'Cross Model Endpoint', {value:_LLMStack._rerankEndPoint || 'No Cross Endpoint Created'});
    new CfnOutput(this, 'Embedding Model Endpoint', {value:_LLMStack._embeddingEndPoints[0] || 'No Embedding Endpoint Created'});
    new CfnOutput(this, 'Instruct Model Endpoint', {value:_LLMStack._instructEndPoint || 'No Instruct Endpoint Created'});
    new CfnOutput(this, 'Processed Object Table', {value:_EtlStack._processedObjectsTable});
    new CfnOutput(this, 'Chunk Bucket', {value:_EtlStack._resBucketName});
    new CfnOutput(this, '_aosIndexDict', {value:_CdkParameters._OpenSearchIndexDict.valueAsString});
  }

  private setBuildConfig() {
    BuildConfig.DEPLOYMENT_MODE = this.node.tryGetContext('DeploymentMode') ?? 'ALL';
    BuildConfig.LAYER_PIP_OPTION = this.node.tryGetContext('LayerPipOption') ?? '';
    BuildConfig.JOB_PIP_OPTION = this.node.tryGetContext('JobPipOption') ?? '';
  }

}

// for development, use account/region from cdk cli
const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

new RootStack(app, 'llm-bot-dev', { env: devEnv });

app.synth();