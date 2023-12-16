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
    _rerankModelPrefix;
    _rerankModelVersion;
    _embeddingModelPrefix;
    _embeddingModelVersion;
    _instructCodePrefix;
    _etlCodePrefix;

    constructor(scope: Construct, id: string, props: assetsStackProps) {
        super(scope, id, props);

        // Prepare model asset to download from Hugging Face follow script

        // Check if _s3ModelAssets is provided, create a new s3 bucket if not
        const _S3Bucket = props._s3ModelAssets ? s3.Bucket.fromBucketName(this, 'llm-rag', props._s3ModelAssets) : new s3.Bucket(this, 'llm-rag', {
            // Fixed name for serving.properties for now, default is llm-rag inherit from main stack
            bucketName: props._s3ModelAssets,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        });

        // const rerankModelPrefix = props._s3BucketPrefix
        const rerankModelPrefix = "bge-reranker-large"
        const rerankModelVersion = "27c9168d479987529781de8474dff94d69beca11"
        const rerankCodePrefix = "bge-reranker-large_deploy_code"
        // const embeddingModelPrefix = 'buffer-embedding-002-model'
        const embeddingModelPrefix: readonly string[] = ['bge-large-zh-v1-5', 'bge-large-en-v1-5']
        const embeddingModelVersion: readonly string[] = ['b5c9d86d763d9945f7c0a73e549a4a39c423d520', '5888da4a3a013e65d33dd6f612ecd4625eb87a7d']
        const embeddingCodePrefix = 'buffer_embedding_002_deploy_code'
        const instructModelPrefix = 'buffer-instruct-003-model'
        const instructCodePrefix = 'buffer_instruct_003_deploy_code'
        // const etlModelPrefix = 'buffer-etl-model'
        const etlCodePrefix = 'buffer_etl_deploy_code'

        // rerank MODEL
        // Define a local asset for code
        const rerankCodeAsset = new s3assets.Asset(this, 'rerankCodeAsset', {
            path: join(__dirname, '../../../model/rerank/code'),
        });

        const rerankCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'rerankCodeAssetDeployment', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../model/rerank/code'))],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: rerankCodePrefix,
        });
        // this._rerankCodePrefix = rerankCodePrefix
        this._rerankModelPrefix = rerankModelPrefix
        this._rerankModelVersion = rerankModelVersion 

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
        // this._embeddingCodePrefix = embeddingCodePrefix
        this._embeddingModelPrefix = embeddingModelPrefix
        this._embeddingModelVersion = embeddingModelVersion

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

        // ETL MODEL
        // Define a local asset for code
        const etlCodeAsset = new s3assets.Asset(this, 'etlCodeAsset', {
            path: join(__dirname, '../../../model/etl/code'),
        });

        const etlCodeAssetDeployment = new s3deploy.BucketDeployment(this, 'etlCodeAssetDeployment', {
            sources: [s3deploy.Source.asset(join(__dirname, '../../../model/etl/code'))],
            destinationBucket: _S3Bucket,
            destinationKeyPrefix: etlCodePrefix,
        });
        this._etlCodePrefix = etlCodePrefix

        // Skip the deployment if _s3ModelAssets is provided
        if (!props._s3ModelAssets) {
            // Define a local asset for model
            const rerankModelAsset = new s3assets.Asset(this, 'ModelAsset', {
                path: join(__dirname, '../../../model/rerank/model'),
            });
            const rerankModelAssetDeployment = new s3deploy.BucketDeployment(this, 'rerankModelAssetDeployment', {
                sources: [s3deploy.Source.asset(join(__dirname, '../../../model/rerank/model'))],
                destinationBucket: _S3Bucket,
                destinationKeyPrefix: rerankModelPrefix,
                // memoryLimit: 4096,
            });

            // Define a local asset for model
            const embeddingModelAsset = new s3assets.Asset(this, 'embeddingModelAsset', {
                path: join(__dirname, '../../../model/embedding/model'),
            });
            const embeddingModelAssetDeployment = new s3deploy.BucketDeployment(this, 'embeddingModelAssetDeployment', {
                sources: [s3deploy.Source.asset(join(__dirname, '../../../model/embedding/model'))],
                destinationBucket: _S3Bucket,
                destinationKeyPrefix: embeddingModelPrefix[0],
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