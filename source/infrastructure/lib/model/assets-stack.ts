import { NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { join } from "path";
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

        // Check if _s3ModelAssets is provided, create a new s3 bucket if not
        const _S3Bucket = props._s3ModelAssets ? s3.Bucket.fromBucketName(this, 'llm-rag', props._s3ModelAssets) : new s3.Bucket(this, 'llm-rag', {
            // Fixed name for serving.properties for now, default is llm-rag inherit from main stack
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
            path: join(__dirname, '../../../model/cross/code'),
        });

        const crossCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'crossCodeAssetDeployment', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../model/cross/code'))],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: crossCodePrefix,
        });
        this._crossCodePrefix = crossCodePrefix

        // EMBEDDING MODEL
        // Define a local asset for code
        const embeddingCodeAsset = new s3assets.Asset(this, 'embeddingCodeAsset', {
            path: join(__dirname, '../../../model/embedding/code'),
        });

        const embeddingCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'embeddingCodeAssetDeployment', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../model/embedding/code'))],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: embeddingCodePrefix,
        });
        this._embeddingCodePrefix = embeddingCodePrefix

        // INSTRUCT MODEL
        // Define a local asset for code
        const instructCodeAsset = new s3assets.Asset(this, 'instructCodeAsset', {
            path: join(__dirname, '../../../model/instruct/code'),
        });

        const instructCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'instructCodeAssetDeployment', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../model/instruct/code'))],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: instructCodePrefix,
        });
        this._instructCodePrefix = instructCodePrefix

        // Skip the deployment if _s3ModelAssets is provided
        if (!props._s3ModelAssets) {
            // Define a local asset for model
            const crossModelAsset = new s3assets.Asset(this, 'ModelAsset', {
                path: join(__dirname, '../../../model/cross/model'),
            });
            const crossModelAssetDeployment = new s3deploy.BucketDeployment(this, 'crossModelAssetDeployment', {
                sources: [s3deploy.Source.asset(join(__dirname, '../../../model/cross/model'))],
                destinationBucket: _S3Bucket,
                destinationKeyPrefix: crossModelPrefix,
                // memoryLimit: 4096,
            });

            // Define a local asset for model
            const embeddingModelAsset = new s3assets.Asset(this, 'embeddingModelAsset', {
                path: join(__dirname, '../../../model/embedding/model'),
            });
            const embeddingModelAssetDeployment = new s3deploy.BucketDeployment(this, 'embeddingModelAssetDeployment', {
                sources: [s3deploy.Source.asset(join(__dirname, '../../../model/embedding/model'))],
                destinationBucket: _S3Bucket,
                destinationKeyPrefix: embeddingModelPrefix,
            });

            // Define a local asset for model
            const instructModelAsset = new s3assets.Asset(this, 'instructModelAsset', {
                path: join(__dirname, '../../../model/instruct/model'),
            });

            const instructModelAssetDeployment = new s3deploy.BucketDeployment(this, 'instructModelAssetDeployment', {
                sources: [s3deploy.Source.asset(join(__dirname, '../../../model/instruct/model'))],
                destinationBucket: _S3Bucket,
                destinationKeyPrefix: instructModelPrefix,
            });
        }
    }
}