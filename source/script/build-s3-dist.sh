#!/bin/bash

set -euxo pipefail

__dir="$(cd "$(dirname $0)";pwd)"
SRC_PATH="${__dir}/.."

lambda_source_dir="$SRC_PATH/lambda"
lib_dir="$lambda_source_dir/deployment_assets"
lambda_build_dist_dir="$lib_dir/lambda_assets"

echo "--------------------------------------------"
echo "[Init] Clean existed dist folders"
echo "--------------------------------------------"
echo "rm -rf $lambda_build_dist_dir"
rm -rf $lambda_build_dist_dir
echo "mkdir -p $lambda_build_dist_dir"
mkdir -p $lambda_build_dist_dir
rm -rf $lambda_source_dir/prompt_management/package
rm -rf $lambda_source_dir/prompt_management/common_logic
rm -rf $lambda_source_dir/intention/aos/sm_utils.py

# echo "--------------------------------------------"
# echo "[Packing] PromptManagement Lambda function"
# echo "--------------------------------------------"
# mkdir -p "$lambda_source_dir"/prompt_management/shared
# # cp "$lambda_source_dir"/online/common_logic/common_utils/constant.py "$lambda_source_dir"/prompt_management/common_logic/common_utils
# # cp "$lambda_source_dir"/online/common_logic/common_utils/prompt_utils.py "$lambda_source_dir"/prompt_management/common_logic/common_utils
# cd "$lambda_source_dir"/prompt_management || exit 1
# zip -q -r9 "$lambda_build_dist_dir"/prompt_management.zip .


# echo "--------------------------------------------"
# echo "[Packing] IntentionManagement Lambda function"
# echo "--------------------------------------------"
# cp "$lambda_source_dir"/job/dep/llm_bot_dep/sm_utils.py "$lambda_source_dir"/intention/aos
