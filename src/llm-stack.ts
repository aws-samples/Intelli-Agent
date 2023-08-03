import { NestedStack, StackProps, RemovalPolicy, Aws} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';

import * as dotenv from "dotenv";
dotenv.config();

interface llmStackProps extends StackProps {
    _vpc: ec2.Vpc;
    _securityGroup: ec2.SecurityGroup;
    _domainEndpoint: string;
}

export class LLMStack extends NestedStack {
    _endPointName;

    constructor(scope: Construct, id: string, props: llmStackProps) {
        super(scope, id, props);

        // Prepare model asset to download from Hugging Face follow script

        // Specify s3 bucket and prefix for model
        const _S3Bucket = new s3.Bucket(this, 'llm-rag', {
            // Fixed name for serving.properties
            bucketName: "llm-rag",
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        const modelPrefix = 'buffer-cross-001-model'
        const codePrefix = 'buffer_cross_001_deploy_code'

        // Define a local asset for code
        const codeAsset = new s3assets.Asset(this, 'CodeAsset', {
            path: 'src/models/cross/code',
        });

        const codeAssetDeployment = new s3deploy.BucketDeployment(this, 'codeAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/cross/code')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: codePrefix,
        });

        // Define a local asset
        const modelAsset = new s3assets.Asset(this, 'ModelAsset', {
            path: 'src/models/cross/model',
        });

        const modelAssetDeployment = new s3deploy.BucketDeployment(this, 'modelAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/cross')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: modelPrefix,
        });

        // Create execution role
        const executionRole = new iam.Role(this, 'executionRole', {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
        });

        executionRole.addToPolicy(new iam.PolicyStatement({
            actions: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject',
                's3:ListBucket',
            ],
            resources: [
                _S3Bucket.bucketArn,
                `${_S3Bucket.bucketArn}/*`,
            ],
        }));

        executionRole.addToPolicy(new iam.PolicyStatement({
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources: ['*'],
        }));

        // Create model
        const inference_image_uri = '763104351884.dkr.ecr.'+ Aws.REGION +'.amazonaws.com/djl-inference:0.21.0-deepspeed0.8.3-cu117'
        const model = new sagemaker.CfnModel(this, 'cross-model', {
            executionRoleArn: executionRole.roleArn,
            primaryContainer: {
                image: inference_image_uri,
                modelDataUrl: `s3://${_S3Bucket.bucketName}/${codePrefix}`,
                environment: {
                    S3_CODE_PREFIX: codePrefix,
                },
            },
        });

        // const baseName = 'buffer-cross-001';
        // const timestamp = Date.now();
        // const modelName = `${baseName}-${timestamp}`;

        // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
        const endpointConfig = new sagemaker.CfnEndpointConfig(this, 'cross-endpoint-config', {
            productionVariants: [{
                initialVariantWeight: 1.0,
                modelName: model.attrModelName,
                variantName: 'variantProd',
                containerStartupHealthCheckTimeoutInSeconds: 15*60,
                initialInstanceCount: 1,
                instanceType: 'ml.g4dn.xlarge',
            }],
        });

        // Create endpoint
        const endpoint = new sagemaker.CfnEndpoint(this, 'cross-endpoint', {
            endpointConfigName: endpointConfig.ref!,
            endpointName: 'cross-endpoint',
        });

        this._endPointName = endpoint.endpointName;
    }
}