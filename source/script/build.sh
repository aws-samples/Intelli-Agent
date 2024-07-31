#!/bin/bash

set -e

# Load config.json
config_file="../infrastructure/bin/config.json"
knowledge_base_enabled=$(jq -r '.knowledgeBase.enabled' $config_file)
knowledge_base_models_enabled=$(jq -r '.knowledgeBase.knowledgeBaseModels.enabled' $config_file)
ecr_repository=$(jq -r '.knowledgeBase.knowledgeBaseModels.ecrRepository' $config_file)
ecr_image_tag=$(jq -r '.knowledgeBase.knowledgeBaseModels.ecrImageTag' $config_file)
rag_enabled=$(jq -r '.rag.enabled' $config_file)
model_assets_bucket=$(jq -r '.sagemaker.modelAssetsBucket' $config_file)
ui_enabled=$(jq -r '.ui.enabled' $config_file)

echo "Knowledge Base Enabled: $knowledge_base_enabled"
echo "Knowledge Base Models Enabled: $knowledge_base_models_enabled"
echo "ECR Repository: $ecr_repository"
echo "ECR Image Tag: $ecr_image_tag"
echo "RAG Enabled: $rag_enabled"
echo "Model Assets Bucket: $model_assets_bucket"
echo "UI Enabled: $ui_enabled"


prepare_etl_model() {
    echo "Prepare ETL Model"
    cd model/etl/code
    sh model.sh ./Dockerfile $ecr_repository $ecr_image_tag
    cd - > /dev/null
    pwd
}

prepare_online_model() {
    echo "Prepare Online Model"
    cd model
    bash prepare_model.sh -s $model_assets_bucket
    cd - > /dev/null
}

build_frontend() {
    echo "Build Frontend"
    cd portal
    npm install && npm run build
    cd - > /dev/null
}

modules_prepared=""
cd ..

if $knowledge_base_enabled && $knowledge_base_models_enabled; then
    prepare_etl_model
    modules_prepared="${modules_prepared}ETL Model, "
fi

if $rag_enabled; then
    prepare_online_model
    modules_prepared="${modules_prepared}Online Model, "
fi

if $ui_enabled; then
    build_frontend
    modules_prepared="${modules_prepared}Frontend, "
fi

aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

# Remove the trailing comma and space
modules_prepared=$(echo "$modules_prepared" | sed 's/, $//')

if [ -n "$modules_prepared" ]; then
    echo "You have prepared assets for the following modules: $modules_prepared."
else
    echo "No modules were prepared."
fi