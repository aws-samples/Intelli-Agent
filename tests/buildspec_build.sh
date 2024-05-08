#!/bin/bash

export STACK_NAME="llm-bot-dev"
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export API_BUCKET=llm-bot-documents-$ACCOUNT_ID-$AWS_DEFAULT_REGION

# TODO: Change the value of API_BUCKET when the resources are cleaned up
if [ "$CLEAN_RESOURCES" = "yes" ]; then
   export API_BUCKET=llm-bot-documents-$ACCOUNT_ID-$AWS_DEFAULT_REGION-$CODEBUILD_BUILD_NUMBER
fi

echo "export ACCOUNT_ID=$ACCOUNT_ID" > env.properties
echo "export API_BUCKET=$API_BUCKET" >> env.properties
echo "export STACK_NAME=$STACK_NAME" >> env.properties

aws cloudformation delete-stack --stack-name "$STACK_NAME"

aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"

echo "----------------------------------------------------------------"
echo "$DEPLOY_STACK deploy start..."
echo "----------------------------------------------------------------"
STARTED_TIME=$(date +%s)

if [ "$DEPLOY_STACK" = "cdk" ]; then
    pushd "llm-bot/source/infrastructure"
    npm i -g pnpm
    pnpm i
    npx cdk deploy --parameters SubEmail=example@amazon.com \
                  --parameters S3ModelAssets="$S3_MODEL_ASSETS_BUCKET" \
                  --parameters EtlImageName="$ETL_IMAGE_NAME" \
                  --parameters ETLTag="$ETL_IMAGE_TAG" \
                  --require-approval never
   popd
fi

python --version
sudo yum install wget -y

cd llm-bot/test || exit 1
make build

FINISHED_TIME=$(date +%s)
export DEPLOY_DURATION_TIME=$(( $FINISHED_TIME - $STARTED_TIME ))
echo "export DEPLOY_DURATION_TIME=$DEPLOY_DURATION_TIME" >> env.properties

echo "----------------------------------------------------------------"
echo "Get api gateway url & token"
echo "----------------------------------------------------------------"
stack_info=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME")
export API_GATEWAY_URL=$(echo "$stack_info" | jq -r '.Stacks[0].Outputs[] | select(.OutputKey=="APIEndpointAddress").OutputValue')
echo "export API_GATEWAY_URL=$API_GATEWAY_URL" >> env.properties
echo "export API_GATEWAY_URL_TOKEN=$API_GATEWAY_URL_TOKEN" >> env.properties

set -euxo pipefail

echo "----------------------------------------------------------------"
echo "Running pytest..."
echo "----------------------------------------------------------------"
API_TEST_STARTED_TIME=$(date +%s)
echo "export API_TEST_STARTED_TIME=$API_TEST_STARTED_TIME" >> env.properties
source venv/bin/activate
pytest ./ --exitfirst -rA --log-cli-level="INFO" --json-report --json-report-summary --json-report-file=detailed_report.json --html="report-${CODEBUILD_BUILD_NUMBER}.html" --self-contained-html --continue-on-collection-errors
FINISHED_TIME=$(date +%s)