import { NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import * as dotenv from "dotenv";
import * as cdk from 'aws-cdk-lib';
import { BuildConfig } from '../../lib/shared/build-config';

dotenv.config();

interface llmStackProps extends StackProps {
    _s3ModelAssets: string;
    _rerankModelPrefix: string;
    _rerankModelVersion: string;
    _embeddingModelPrefix: string[];
    _embeddingModelVersion: string[];
    _instructModelPrefix: string;
    _instructModelVersion: string;
}

export class LLMStack extends NestedStack {
    _rerankEndPoint: string = '';
    _embeddingEndPoints: string[] = [];
    _instructEndPoint: string = '';

    constructor(scope: Construct, id: string, props: llmStackProps) {
        super(scope, id, props);

        const llmImageUrlDomain = (this.region === 'cn-north-1' || this.region === 'cn-northwest-1')
            ? '.amazonaws.com.cn/'
            : '.amazonaws.com/';

        const llmImageUrlAccount = (this.region === 'cn-north-1' || this.region === 'cn-northwest-1')
            ? '727897471807.dkr.ecr.'
            : '763104351884.dkr.ecr.';

        // Create IAM execution role
        const executionRole = new iam.Role(this, 'llmbot-endpoint-execution-role', {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
            ],
        });

        console.log('LLM Stack BuildConfig.DEPLOYMENT_MODE: ', BuildConfig.DEPLOYMENT_MODE);

        // If Deplyment mode is OFFLINE_OPENSEARCH or ALL, then create the following resources
        if (BuildConfig.DEPLOYMENT_MODE === 'OFFLINE_OPENSEARCH' || BuildConfig.DEPLOYMENT_MODE === 'ALL') {

            // EMBEDDING MODEL
            for (let i = 0; i < props._embeddingModelPrefix.length; i++) {
                const modelPrefix = props._embeddingModelPrefix[i];
                const codePrefix = modelPrefix + "_deploy_code";
                const versionId = props._embeddingModelVersion[i]
                const currentEndpointName = "embedding-" + modelPrefix + "-" + versionId.slice(0, 5)
                const stackModelName = "embedding-model-" + versionId.slice(0, 5)
                const stackConfigName = "embedding-endpoint-config-" + versionId.slice(0, 5)
                const stackEndpointName = "embedding-endpoint-name-" + versionId.slice(0, 5)
                // EMBEDDING MODEL
                // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
                const embeddingImageUrl = llmImageUrlAccount + this.region + llmImageUrlDomain + 'djl-inference:0.21.0-deepspeed0.8.3-cu117'
                const embeddingModel = new sagemaker.CfnModel(this, stackModelName, {
                    executionRoleArn: executionRole.roleArn,
                    primaryContainer: {
                        image: embeddingImageUrl,
                        modelDataUrl: `s3://${props._s3ModelAssets}/${codePrefix}/s2e_model.tar.gz`,
                        environment: {
                            S3_CODE_PREFIX: codePrefix,
                        },
                    },
                });

                // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
                const embeddingEndpointConfig = new sagemaker.CfnEndpointConfig(this, stackConfigName, {
                    productionVariants: [{
                        initialVariantWeight: 1.0,
                        modelName: embeddingModel.attrModelName,
                        variantName: 'variantProd',
                        containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
                        initialInstanceCount: 1,
                        instanceType: 'ml.g4dn.xlarge',
                    }],
                });

                // Create endpoint
                const tag: cdk.CfnTag = {
                    key: 'version',
                    value: versionId,
                };

                const tag_array = [tag]

                const embeddingEndpoint = new sagemaker.CfnEndpoint(this, stackEndpointName, {
                    endpointConfigName: embeddingEndpointConfig.attrEndpointConfigName,
                    endpointName: currentEndpointName,
                    tags: tag_array,
                });

                if (typeof embeddingEndpoint.endpointName != 'undefined') {
                    this._embeddingEndPoints.push(embeddingEndpoint.endpointName);
                }

            }
        }

        if (BuildConfig.DEPLOYMENT_MODE === 'OFFLINE_OPENSEARCH') {
            console.log('Value is true');
        } else if (BuildConfig.DEPLOYMENT_MODE === 'ALL') {
            // Rerank MODEL
            const rerankModelPrefix = props._rerankModelPrefix;
            const rerankCodePrefix = rerankModelPrefix + "_deploy_code";
            const rerankVersionId = props._rerankModelVersion
            const rerankEndpointName = "rerank-" + rerankModelPrefix + "-" + rerankVersionId.slice(0, 5)
            // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
            const rerankImageUrl = llmImageUrlAccount + this.region + llmImageUrlDomain + 'djl-inference:0.21.0-deepspeed0.8.3-cu117'
            const rerankModel = new sagemaker.CfnModel(this, 'rerank-model', {
                executionRoleArn: executionRole.roleArn,
                primaryContainer: {
                    image: rerankImageUrl,
                    modelDataUrl: `s3://${props._s3ModelAssets}/${rerankCodePrefix}/rerank_model.tar.gz`,
                    environment: {
                        S3_CODE_PREFIX: rerankCodePrefix,
                    },
                },
            });

            // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
            const rerankEndpointConfig = new sagemaker.CfnEndpointConfig(this, 'rerank-endpoint-config', {
                productionVariants: [{
                    initialVariantWeight: 1.0,
                    modelName: rerankModel.attrModelName,
                    variantName: 'variantProd',
                    containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
                    initialInstanceCount: 1,
                    instanceType: 'ml.g4dn.2xlarge',
                }],
            });

            // Create endpoint
            const rerank_tag: cdk.CfnTag = {
                key: 'version',
                value: rerankVersionId,
            };

            const rerank_tag_array = [rerank_tag]

            // Create endpoint
            const rerankEndpoint = new sagemaker.CfnEndpoint(this, 'rerank-endpoint', {
                endpointConfigName: rerankEndpointConfig.attrEndpointConfigName,
                endpointName: rerankEndpointName,
                tags: rerank_tag_array,
            });

            this._rerankEndPoint = rerankEndpoint.endpointName as string;

            // INSTRUCT MODEL
            // Create model, BucketDeployment construct automatically handles dependencies to ensure model assets uploaded before creating the model in this.region
            // Instruct MODEL
            const InstructModelPrefix = props._instructModelPrefix;
            const InstructCodePrefix = InstructModelPrefix + "_deploy_code";
            const InstructVersionId = props._instructModelVersion;
            const InstructEndpointName = "instruct-" + InstructModelPrefix + "-" + InstructVersionId.slice(0, 5)

            const instructImageUrl = llmImageUrlAccount + this.region + llmImageUrlDomain + 'djl-inference:0.25.0-deepspeed0.11.0-cu118'
            const instructModel = new sagemaker.CfnModel(this, 'instruct-model', {
                executionRoleArn: executionRole.roleArn,
                primaryContainer: {
                    image: instructImageUrl,
                    modelDataUrl: `s3://${props._s3ModelAssets}/${InstructCodePrefix}/llm_model.tar.gz`,
                    environment: {
                        S3_CODE_PREFIX: InstructCodePrefix,
                    },
                },
            });

            // Create endpoint configuration, refer to https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sagemaker.CfnEndpointConfig.html for full options
            const instructEndpointConfig = new sagemaker.CfnEndpointConfig(this, 'instruct-endpoint-config', {
                productionVariants: [{
                    initialVariantWeight: 1.0,
                    modelName: instructModel.attrModelName,
                    variantName: 'variantProd',
                    containerStartupHealthCheckTimeoutInSeconds: 15 * 60,
                    initialInstanceCount: 1,
                    instanceType: 'ml.g4dn.4xlarge',
                }],
            });

            const instruct_tag: cdk.CfnTag = {
                key: 'version',
                value: InstructVersionId,
            };

            const instruct_tag_array = [instruct_tag]

            // Create endpoint
            const InstructEndpoint = new sagemaker.CfnEndpoint(this, 'instruct-endpoint', {
                endpointConfigName: instructEndpointConfig.attrEndpointConfigName,
                endpointName: InstructEndpointName,
                tags: instruct_tag_array,
            });

            this._instructEndPoint = InstructEndpoint.endpointName as string;
        }



    }
}