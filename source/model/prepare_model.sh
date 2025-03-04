set -e

# TODO: function is not supported by sh prepare_model.sh
function usage {
  echo "Make sure python3 installed properly. Usage: $0 -s S3_BUCKET_NAME"
  echo "  -s S3_BUCKET_NAME   S3 bucket name to upload the model"
  exit 1
}

# Parse command-line options
while getopts ":s:" opt; do
  case $opt in
    s) s3_bucket_name="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
    :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
  esac
done

# Validate the hf_token and python3 interpreter exist
if [ -z "$s3_bucket_name" ] || ! command -v python3 &> /dev/null; then
  usage
fi

# Check if the bucket exists
if aws s3 ls "s3://$s3_bucket_name" 2>&1 | grep -q 'NoSuchBucket'
then
  echo "Bucket does not exist. Creating bucket: $BUCKET_NAME"
  # Create the bucket
  aws s3 mb "s3://$s3_bucket_name"
else
  echo "Bucket $s3_bucket_name already exists."
fi

rm -rf model_temp
mkdir model_temp
cd model_temp
wget https://aws-gcr-industry-assets.s3.cn-northwest-1.amazonaws.com.cn/mfg-kb-do-not-delete/object_list.txt

# S3 Bucket URL
S3_BUCKET_URL="https://aws-gcr-industry-assets.s3.cn-northwest-1.amazonaws.com.cn"

# Path to the object list file
OBJECT_LIST_FILE="object_list.txt"

# Loop through each line in the object list file
while IFS= read -r line; do
    # Extract the file path (skip the timestamp and file size columns)
    file_path=$(echo $line | awk '{print $NF}')
    
    if [[ "$file_path" == */ ]]; then
        mkdir -p "$file_path"
    else
        dir=$(dirname "$file_path")
        mkdir -p "$dir"
        
        wget --no-check-certificate "$S3_BUCKET_URL/$file_path" -O "$file_path"
    fi
done < "$OBJECT_LIST_FILE"

# Update S3 url
cd mfg-kb-do-not-delete/bce-embedding-base_deploy_code
tar xzvf bce_embedding_model.tar.gz
rm -rf requirements.txt
cp ../../../requirements_cn.txt requirements.txt
if [ "$os_type" == "Darwin" ]; then
  sed -i "" "s|option.s3url = s3://intelli-agent-models-817734611975-us-west-2|option.s3url = s3://$s3_bucket_name|g" serving.properties
else
  sed -i "s|option.s3url = s3://intelli-agent-models-817734611975-us-west-2|option.s3url = s3://$s3_bucket_name|g" serving.properties
fi

if [ -f bce_embedding_model.tar.gz ]; then
  rm bce_embedding_model.tar.gz
fi
tar czvf bce_embedding_model.tar.gz *
rm -rf requirements.txt
rm -rf serving.properties
rm -rf model.py
rm -rf ../bce-embedding-and-bge-reranker_deploy_code/*
cp bce_embedding_model.tar.gz ../bce-embedding-and-bge-reranker_deploy_code/


cd ../bge-reranker-large_deploy_code
tar xzvf bge_reranker_model.tar.gz
rm -rf requirements.txt
cp ../../../requirements_cn.txt requirements.txt
if [ "$os_type" == "Darwin" ]; then
  sed -i "" "s|option.s3url = s3://intelli-agent-models-817734611975-us-west-2|option.s3url = s3://$s3_bucket_name|g" serving.properties
else
  sed -i "s|option.s3url = s3://intelli-agent-models-817734611975-us-west-2|option.s3url = s3://$s3_bucket_name|g" serving.properties
fi

if [ -f bge_reranker_model.tar.gz ]; then
  rm bge_reranker_model.tar.gz
fi
tar czvf bge_reranker_model.tar.gz *
rm -rf requirements.txt
rm -rf serving.properties
rm -rf model.py
cp bge_reranker_model.tar.gz ../bce-embedding-and-bge-reranker_deploy_code/
cd ../../..


aws s3 sync model_temp/mfg-kb-do-not-delete s3://$s3_bucket_name

echo "Successfully prepared model for Intelli-Agent."