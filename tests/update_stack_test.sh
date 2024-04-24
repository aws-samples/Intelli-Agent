set -euxo pipefail

export STACK_NAME="Extension-for-Stable-Diffusion-on-AWS"
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export API_BUCKET=esd-test-$ACCOUNT_ID-$AWS_DEFAULT_REGION

aws cloudformation delete-stack --stack-name "$STACK_NAME"
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"

echo "deploy latest online version..."
aws cloudformation create-stack --stack-name "$STACK_NAME" \
                               --template-url "https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json" \
                               --capabilities CAPABILITY_NAMED_IAM \
                               --parameters ParameterKey=Email,ParameterValue="example@example.com" \
                                            ParameterKey=Bucket,ParameterValue="$API_BUCKET" \
                                            ParameterKey=LogLevel,ParameterValue="INFO" \
                                            ParameterKey=SdExtensionApiKey,ParameterValue="09876743210987654322"
aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME"


echo "update to dev version..."
aws cloudformation update-stack --stack-name "$STACK_NAME" \
                               --template-url "https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/dev/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json" \
                               --capabilities CAPABILITY_NAMED_IAM \
                               --parameters ParameterKey=Email,ParameterValue="example@example.com" \
                                            ParameterKey=Bucket,ParameterValue="$API_BUCKET" \
                                            ParameterKey=LogLevel,ParameterValue="INFO" \
                                            ParameterKey=SdExtensionApiKey,ParameterValue="09876743210987654322"
aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME"

aws cloudformation delete-stack --stack-name "$STACK_NAME"
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"