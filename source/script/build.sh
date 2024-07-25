#!/bin/bash

set -e

print_usage() {
    echo "Usage: $0 [-b s3_bucket_name] [-i etl_image_name] [-t etl_image_tag] [-e] [-o] [-f]"
    echo
    echo "Options:"
    echo "  -e  Prepare ETL Model"
    echo "  -o  Prepare Online Model"
    echo "  -f  Build Frontend"
    echo
    echo "Examples:"
    echo "  $0 -b my-s3-bucket -i my-etl-image -t latest -e -o -f"
    exit 1
}

prepare_etl_model() {
    echo "Prepare ETL Model"
    cd model/etl/code
    sh model.sh ./Dockerfile $etl_image_name $etl_image_tag
    cd - > /dev/null
    pwd
}

prepare_online_model() {
    echo "Prepare Online Model"
    cd model
    bash prepare_model.sh -s $s3_bucket_name
    cd - > /dev/null
}

build_frontend() {
    echo "Build Frontend"
    cd portal
    npm install && npm run build
    cd - > /dev/null
}

account=$(aws sts get-caller-identity --query Account --output text)
aws_region=$(aws configure get region)
s3_bucket_name="intelli-agent-models-${account}-${aws_region}"
etl_image_name="intelli-agent-etl"
etl_image_tag="latest"
etl_model=false
online_model=false
frontend=false

while getopts "b:i:t:r:eof" opt; do
    case ${opt} in
        b) s3_bucket_name="$OPTARG" ;;
        i) etl_image_name="$OPTARG" ;;
        t) etl_image_tag="$OPTARG" ;;
        e) etl_model=true ;;
        o) online_model=true ;;
        f) frontend=true ;;
        *) print_usage ;;
    esac
done

echo "S3 bucket name: $s3_bucket_name"
echo "ETL image name: $etl_image_name"
echo "ETL image tag: $etl_image_tag"
echo "AWS region: $aws_region"
echo "Prepare ETL Model: $etl_model"
echo "Prepare Online Model: $online_model"
echo "Build Frontend: $frontend"

echo "Install dependencies"
cd ..
cd infrastructure
npm install
pwd
cd - > /dev/null
pwd

modules_prepared=""

if $etl_model; then
    prepare_etl_model
    modules_prepared="${modules_prepared}ETL Model, "
fi

if $online_model; then
    prepare_online_model
    modules_prepared="${modules_prepared}Online Model, "
fi

if $frontend; then
    build_frontend
    modules_prepared="${modules_prepared}Frontend, "
fi

# Remove the trailing comma and space
modules_prepared=$(echo "$modules_prepared" | sed 's/, $//')

if [ -n "$modules_prepared" ]; then
    echo "You have prepared assets for the following modules: $modules_prepared."
else
    echo "No modules were prepared."
fi