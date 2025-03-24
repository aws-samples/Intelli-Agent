#!/bin/bash

set -e

# Load config.json
config_file="../infrastructure/bin/config.json"
deploy_region=$(jq -r '.deployRegion' $config_file)
knowledge_base_enabled=$(jq -r '.knowledgeBase.enabled' $config_file)
knowledge_base_intelliagent_enabled=$(jq -r '.knowledgeBase.knowledgeBaseType.intelliAgentKb.enabled' $config_file)
knowledge_base_models_enabled=$(jq -r '.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.enabled' $config_file)
ecr_repository=$(jq -r '.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrRepository' $config_file)
ecr_image_tag=$(jq -r '.knowledgeBase.knowledgeBaseType.intelliAgentKb.knowledgeBaseModel.ecrImageTag' $config_file)
opensearch_enabled=$(jq -r '.knowledgeBase.knowledgeBaseType.intelliAgentKb.vectorStore.opensearch.enabled' $config_file)
embedding_model_provider=$(jq -r '.model.embeddingsModels[0].provider' $config_file)
model_assets_bucket=$(jq -r '.model.modelConfig.modelAssetsBucket' $config_file)
ui_enabled=$(jq -r '.ui.enabled' $config_file)
use_open_source_llm=$(jq -r '.chat.useOpenSourceLLM' $config_file)
# fi

echo "Knowledge Base Enabled: $knowledge_base_enabled"
echo "IntelliAgent Knowledge Base Enabled: $knowledge_base_intelliagent_enabled"
echo "Knowledge Base Models Enabled: $knowledge_base_models_enabled"
echo "ECR Repository: $ecr_repository"
echo "ECR Image Tag: $ecr_image_tag"
echo "OpenSearch Enabled: $opensearch_enabled"
echo "Use Open Source Model: $use_open_source_llm"
echo "Model Assets Bucket: $model_assets_bucket"
echo "UI Enabled: $ui_enabled"

# Set ECR login region based on deploy region
if [ "$deploy_region" != "cn-north-1" ] && [ "$deploy_region" != "cn-northwest-1" ]; then
    ecr_login_region="us-east-1"
    aws ecr-public get-login-password --region $ecr_login_region | docker login --username AWS --password-stdin public.ecr.aws
fi

build_lambda_asset() {
    echo "Building Lambda Asset"
    cd script
    bash build-s3-dist.sh
    cd - > /dev/null
}

build_frontend() {
    echo "Building Frontend"
    cd portal
    rm -rf node_modules package-lock.json
    npm install && npm run build
    cd - > /dev/null
}

build_client_frontend() {
    echo "Building Frontend"
    cd cs-portal
    rm -rf node_modules package-lock.json
    npm install && npm run build
    cd - > /dev/null
}

build_etl_package() {
    echo "Building ETL Package"
    cd lambda/job
    sh build_whl.sh
    cd - > /dev/null
}

prepare_etl_model() {
    echo "Preparing ETL Model"
    cd model/etl/code
    sh model.sh $ecr_repository $ecr_image_tag $deploy_region
    cd - > /dev/null
    pwd
}

prepare_online_model() {
    echo "Preparing Online Model"
    cd model
    if [ "$deploy_region" == "cn-north-1" ] || [ "$deploy_region" == "cn-northwest-1" ]; then
        bash prepare_model_cn.sh -s $model_assets_bucket
    else
        bash prepare_model.sh -s $model_assets_bucket
    fi
    cd - > /dev/null
}

build_deployment_module() {
    echo "Building Model Deployment Module"
    # curl https://aws-gcr-solutions-assets.s3.us-east-1.amazonaws.com/emd/wheels/emd-0.5.0-py3-none-any.whl -o emd-0.5.0-py3-none-any.whl && pip install emd-0.5.0-py3-none-any.whl"[all]"
    curl https://aws-gcr-solutions-assets.s3.us-east-1.amazonaws.com/emd/wheels/emd-0.6.0%2B0.6.0.mini-py3-none-any.whl -o emd-0.6.0-py3-none-any.whl && pip install emd-0.6.0-py3-none-any.whl"[all]"
    emd bootstrap
}

modules_prepared=""
cd ..

build_lambda_asset
modules_prepared="${modules_prepared}Lambda Deployment, "

if $ui_enabled; then
    build_frontend
    build_client_frontend
    modules_prepared="${modules_prepared}Frontend, "
fi

if $knowledge_base_enabled && $knowledge_base_intelliagent_enabled; then
    build_etl_package
    modules_prepared="${modules_prepared}ETL Package, "
fi

if $knowledge_base_enabled && $knowledge_base_intelliagent_enabled && $knowledge_base_models_enabled; then
    prepare_etl_model
    modules_prepared="${modules_prepared}ETL Model, "
fi

if $knowledge_base_enabled && $knowledge_base_intelliagent_enabled && $opensearch_enabled && [ "$embedding_model_provider" != "bedrock" ]; then
    prepare_online_model
    modules_prepared="${modules_prepared}Online Model, "
fi

if $use_open_source_llm; then
    build_deployment_module
    modules_prepared="${modules_prepared}Model Deployment, "
fi

# Remove the trailing comma and space
modules_prepared=$(echo "$modules_prepared" | sed 's/, $//')

if [ -n "$modules_prepared" ]; then
    echo "You have prepared assets for the following modules: $modules_prepared."
else
    echo "No modules were prepared."
fi