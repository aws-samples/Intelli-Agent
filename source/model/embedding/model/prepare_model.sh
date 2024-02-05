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

hf_names=("BAAI/bge-large-zh-v1.5" "BAAI/bge-large-en-v1.5")
model_names=("bge-large-zh-v1-5" "bge-large-en-v1-5")
commit_hashs=("b5c9d86d763d9945f7c0a73e549a4a39c423d520" "5888da4a3a013e65d33dd6f612ecd4625eb87a7d")
tensor_parallel_degree=(1 1)

for index in "${!model_names[@]}"; do
  hf_name="${hf_names[$index]}"
  model_name="${model_names[$index]}"
  commit_hash="${commit_hashs[$index]}"
  tp="${tensor_parallel_degree[$index]}"
  echo "model name $model_name"
  echo "commit hash $commit_hash"
  ./model.sh -h $hf_name -m $model_name -c $commit_hash -p $tp -s $s3_bucket_name
done
