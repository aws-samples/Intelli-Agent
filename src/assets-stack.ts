import { NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';

import * as dotenv from "dotenv";
dotenv.config();

interface assetsStackProps extends StackProps {
    _s3ModelAssets: string;
}

export class AssetsStack extends NestedStack {
    _crossCodePrefix;

    constructor(scope: Construct, id: string, props: assetsStackProps) {
        super(scope, id, props);

        // Prepare model asset to download from Hugging Face follow script

        // Specify s3 bucket and prefix for model
        const _S3Bucket = new s3.Bucket(this, 'llm-rag', {
            // Fixed name for serving.properties for now
            bucketName: props._s3ModelAssets,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        // const modelPrefix = props._s3BucketPrefix
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

        // Define a local asset for model
        const modelAsset = new s3assets.Asset(this, 'ModelAsset', {
            path: 'src/models/cross/model',
        });

        const modelAssetDeployment = new s3deploy.BucketDeployment(this, 'modelAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/cross/model')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: modelPrefix,
        });

        this._crossCodePrefix = codePrefix
    }
}