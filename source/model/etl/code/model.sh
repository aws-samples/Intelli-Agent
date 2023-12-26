#!/usr/bin/env bash

# Build the docker image and push it to ECR

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
dockerfile=$1
image=$2
region=$3

if [ "$image" = "" ] || [ "$dockerfile" = "" ] || [ "$region" = "" ]
then
    echo "Usage: $0 <docker-file> <image-name> <aws-region>"
    exit 1
fi

# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi

# Get the region defined in the current configuration (default to us-west-2 if none defined)
image_name="${image}"

# Check if aws-cn is in the ARN
if [ "$(aws sts get-caller-identity --query Arn --output text | cut -d':' -f2)" == "aws-cn" ]; then
    fullname="${account}.dkr.ecr.${region}.amazonaws.com.cn/${image_name}:latest"
else
    fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image_name}:latest"
fi

# If the repository doesn't exist in ECR, create it.
desc_output=$(aws ecr describe-repositories --repository-names ${image_name} 2>&1)

if [ $? -ne 0 ]
then
    if echo ${desc_output} | grep -q RepositoryNotFoundException
    then
        aws ecr create-repository --repository-name "${image_name}" > /dev/null
    else
        >&2 echo ${desc_output}
    fi
fi

# Get the login command from ECR and execute it directly, check the aws-cn for different partition
if [ "$(aws sts get-caller-identity --query Arn --output text | cut -d':' -f2)" == "aws-cn" ]; then
    aws ecr get-login-password --region cn-north-1 | docker login --username AWS --password-stdin 727897471807.dkr.ecr.cn-north-1.amazonaws.com.cn
else
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 763104351884.dkr.ecr.us-east-1.amazonaws.com
fi

# mkdir build
cp ${dockerfile} .

docker build -t ${image_name} -f ${dockerfile} .
docker tag ${image_name} ${fullname}

docker push ${fullname}

