set -e

function usage {
  echo "Make sure python3 installed properly. Usage: $0 -t TOKEN [-m MODEL_NAME] [-c COMMIT_HASH] [-s S3_BUCKET_NAME]"
  echo "  -t TOKEN                             Hugging Face token "
  echo "  -h Hugging Face Repo Name            Hugging Face repo "
  echo "  -m MODEL_NAME                        Model name (default: csdc-atl/buffer-cross-001)"
  echo "  -c COMMIT_HASH                       Commit hash (default: 46d270928463db49b317e5ea469a8ac8152f4a13)"
  echo "  -p Tensor Parrallel degree           Parameters in serving.properties "
  echo "  -s S3_BUCKET_NAME                    S3 bucket name to upload the model (default: llm-rag)"
  exit 1
}

# Default values
model_name="csdc-atl/buffer-cross-001"
commit_hash="46d270928463db49b317e5ea469a8ac8152f4a13"
s3_bucket_name="llm-rag" # Default S3 bucket name

# Parse command-line options
while getopts ":t:h:m:c:p:s:" opt; do
  case $opt in
    t) hf_token="$OPTARG" ;;
    h) hf_name="$OPTARG" ;;
    m) model_name="$OPTARG" ;;
    c) commit_hash="$OPTARG" ;;
    p) tensor_parallel_degree="$OPTARG" ;;
    s) s3_bucket_name="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
    :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
  esac
done


# # Validate the hf_token and python3 interpreter exist
# if [ -z "$hf_token" ] || ! command -v python3 &> /dev/null; then
#   usage
# fi

# # Install necessary packages
pip install huggingface-hub -Uqq
pip install -U sagemaker

# Define local model path
local_model_path="./${model_name}"

# Uncomment the line below if you want to create a specific directory for the model
# mkdir -p $local_model_path

# Download model snapshot in current folder without model prefix added
# python3 -c "from huggingface_hub import snapshot_download; from pathlib import Path; snapshot_download(repo_id='$model_name', revision='$commit_hash', cache_dir=Path('.'), token='$hf_token')"
python3 -c "from huggingface_hub import snapshot_download; from pathlib import Path; snapshot_download(repo_id='$hf_name', revision='$commit_hash', cache_dir='$local_model_path')"

# Find model snapshot path with the first search result
model_snapshot_path=$(find $local_model_path -path '*/snapshots/*' -type d -print -quit)
echo "Model snapshot path: $model_snapshot_path"

# s3://<your own bucket>/<model prefix inherit crossModelPrefix from assets stack>
aws s3 cp --recursive $model_snapshot_path s3://$s3_bucket_name/$model_name

# Prepare model.py files according to model name
model_inference_file="./${model_name}_model.py"
cp $model_inference_file ../code/model.py

# Modify the content of serving.properties and re-tar the model
cp serving.properties ../code/serving.properties
cd ../code
file_path="serving.properties"
os_type=$(uname -s)

if [ "$os_type" == "Darwin" ]; then
  sed -i "" "s|option.s3url = S3PATH|option.s3url = s3://$s3_bucket_name/$model_name/|g" $file_path
  sed -i "" "s|option.tensor_parallel_degree=tpd|option.tensor_parallel_degree=$tensor_parallel_degree|g" $file_path
else
  sed -i "s|option.s3url = S3PATH|option.s3url = s3://$s3_bucket_name/$model_name/|g" $file_path
  sed -i "s|option.tensor_parallel_degree=tpd|option.tensor_parallel_degree=$tensor_parallel_degree|g" $file_path
fi

if [ -f bge_reranker_model.tar.gz ]; then
  rm bge_reranker_model.tar.gz
fi
tar czvf bge_reranker_model.tar.gz *

code_path="${model_name}_deploy_code"
aws s3 cp bge_reranker_model.tar.gz s3://$s3_bucket_name/$code_path/bge_reranker_model.tar.gz
