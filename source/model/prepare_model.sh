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

cd embedding/model
hf_names=("BAAI/bge-m3")
model_names=("bge-m3")
commit_hashs=("3ab7155aa9b89ac532b2f2efcc3f136766b91025")
tensor_parallel_degree=(1)

for index in "${!model_names[@]}"; do
  hf_name="${hf_names[$index]}"
  model_name="${model_names[$index]}"
  commit_hash="${commit_hashs[$index]}"
  tp="${tensor_parallel_degree[$index]}"
  echo "model name $model_name"
  echo "commit hash $commit_hash"
  # ./model.sh -h $hf_name -m $model_name -c $commit_hash -p $tp -s $s3_bucket_name
done

cd ../../bce_embedding/model
hf_names=("maidalun1020/bce-embedding-base_v1")
model_names=("bce-embedding-base")
commit_hashs=("43972580a35ceacacd31b95b9f430f695d07dde9")
tensor_parallel_degree=(1)

for index in "${!model_names[@]}"; do
  hf_name="${hf_names[$index]}"
  model_name="${model_names[$index]}"
  commit_hash="${commit_hashs[$index]}"
  tp="${tensor_parallel_degree[$index]}"
  echo "model name $model_name"
  echo "commit hash $commit_hash"
  ./model.sh -h $hf_name -m $model_name -c $commit_hash -p $tp -s $s3_bucket_name
done

cd ../../rerank/model
hf_names=("BAAI/bge-reranker-large") 
model_names=("bge-reranker-large")
commit_hashs=("27c9168d479987529781de8474dff94d69beca11")
tensor_parallel_degree=(1)

for index in "${!model_names[@]}"; do
  hf_name="${hf_names[$index]}"
  model_name="${model_names[$index]}"
  commit_hash="${commit_hashs[$index]}"
  tp="${tensor_parallel_degree[$index]}"
  echo "model name $model_name"
  echo "commit hash $commit_hash"
  ./model.sh -h $hf_name -m $model_name -c $commit_hash -p $tp -s $s3_bucket_name
done

cd ../../instruct/model
hf_names=("internlm/internlm2-chat-20b-4bits") 
model_names=("internlm2-chat-20b")
commit_hashs=("7bae8edab7cf91371e62506847f2e7fdc24c6a65")
tensor_parallel_degree=(1)

for index in "${!model_names[@]}"; do
  hf_name="${hf_names[$index]}"
  model_name="${model_names[$index]}"
  commit_hash="${commit_hashs[$index]}"
  tp="${tensor_parallel_degree[$index]}"
  echo "model name $model_name"
  echo "commit hash $commit_hash"
  # ./model.sh -h $hf_name -m $model_name -c $commit_hash -p $tp -s $s3_bucket_name
done

aws s3 cp --recursive s3://$s3_bucket_name/bce-embedding-base_deploy_code s3://$s3_bucket_name/embedding-and-reranker_deploy_code
aws s3 cp --recursive s3://$s3_bucket_name/bge-reranker-large_deploy_code s3://$s3_bucket_name/embedding-and-reranker_deploy_code