#!/bin/bash

print_usage() {
    echo "Usage: $0 -b s3_bucket_name -i etl_image_name -t etl_image_tag -r aws_region"
    echo
    echo "Examples:"
    echo "  $0 -b my-s3-bucket -i my-etl-image -t latest -r us-west-2"
    echo "  $0 -b another-bucket -i another-etl-image -t v1.0.0 -r us-east-1"
    exit 1
}

while getopts "b:i:t:r:" opt; do
    case ${opt} in
        b) s3_bucket_name="$OPTARG" ;;
        i) etl_image_name="$OPTARG" ;;
        t) etl_image_tag="$OPTARG" ;;
        r) aws_region="$OPTARG" ;;
        *) print_usage ;;
    esac
done

# Check if all required arguments are provided
if [ -z "$s3_bucket_name" ] || [ -z "$etl_image_name" ] || [ -z "$etl_image_tag" ] || [ -z "$aws_region" ]; then
    echo "Error: s3_bucket_name, etl_image_name, etl_image_tag and aws_region parameters are required."
    print_usage
fi

echo "S3 bucket name: $s3_bucket_name"
echo "ETL image name: $etl_image_name"
echo "ETL image tag: $etl_image_tag"
echo "AWS region: $aws_region"

# Add your script logic below
# For example:
# aws s3 cp myfile.txt s3://$s3_bucket_name/
# docker run -d $etl_image_name:$etl_image_tag
# aws configure set region $aws_region

echo "Install dependencies"
pushd ../infrastructure
npm install
popd

echo "Prepare model"
pushd ../model
sh prepare_model.sh -s $s3_bucket_name
popd

pushd ../model/etl/code
sh model.sh ./Dockerfile $etl_image_name $aws_region $etl_image_tag

echo "Build frontend"
pushd ../portal
npm install && npm run build
popd

echo "Login ECR"
pushd ..
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
popd
