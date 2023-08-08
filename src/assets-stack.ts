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
    _embeddingCodePrefix;
    _instructCodePrefix;

    constructor(scope: Construct, id: string, props: assetsStackProps) {
        super(scope, id, props);

        // Prepare model asset to download from Hugging Face follow script

        // Specify s3 bucket and prefix for model
        const _S3Bucket = new s3.Bucket(this, 'llm-rag', {
            // Fixed name for serving.properties for now
            bucketName: props._s3ModelAssets,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        // const crossModelPrefix = props._s3BucketPrefix
        const crossModelPrefix = 'buffer-cross-001-model'
        const crossCodePrefix = 'buffer_cross_001_deploy_code'
        const embeddingModelPrefix = 'buffer-embedding-002-model'
        const embeddingCodePrefix = 'buffer_embedding_002_deploy_code'
        const instructModelPrefix = 'buffer-instruct-003-model'
        const instructCodePrefix = 'buffer_instruct_003_deploy_code'

        // CROSS MODEL
        // Define a local asset for code
        const crossCodeAsset = new s3assets.Asset(this, 'crossCodeAsset', {
            path: 'src/models/cross/code',
        });

        const crossCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'crossCodeAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/cross/code')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: crossCodePrefix,
        });

        // Define a local asset for model
        const crossModelAsset = new s3assets.Asset(this, 'ModelAsset', {
            path: 'src/models/cross/model',
        });

        const crossModelAssetDeployment = new s3deploy.BucketDeployment(this, 'crossModelAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/cross/model')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: crossModelPrefix,
        });

        this._crossCodePrefix = crossCodePrefix

        // EMBEDDING MODEL
        // Define a local asset for code
        const embeddingCodeAsset = new s3assets.Asset(this, 'embeddingCodeAsset', {
            path: 'src/models/embedding/code',
        });

        const embeddingCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'embeddingCodeAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/embedding/code')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: embeddingCodePrefix,
        });

        // Define a local asset for model
        const embeddingModelAsset = new s3assets.Asset(this, 'embeddingModelAsset', {
            path: 'src/models/embedding/model',
        });

        const embeddingModelAssetDeployment = new s3deploy.BucketDeployment(this, 'embeddingModelAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/embedding/model')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: embeddingModelPrefix,
        });

        this._embeddingCodePrefix = embeddingCodePrefix

        // INSTRUCT MODEL
        // Define a local asset for code
        const instructCodeAsset = new s3assets.Asset(this, 'instructCodeAsset', {
            path: 'src/models/instruct/code',
        });

        const instructCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'instructCodeAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/instruct/code')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: instructCodePrefix,
        });

        // Define a local asset for model
        const instructModelAsset = new s3assets.Asset(this, 'instructModelAsset', {
            path: 'src/models/instruct/model',
        });

        const instructModelAssetDeployment = new s3deploy.BucketDeployment(this, 'instructModelAssetDeployment', {
            sources: [s3deploy.Source.asset('src/models/instruct/model')],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: instructModelPrefix,
        });

        this._instructCodePrefix = instructCodePrefix
    }
}