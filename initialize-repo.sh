#!/bin/bash

# This script initializes a git repo using the current directory name as the solution name.
solution_name=`echo ${PWD##*/} | tr '[:upper:]' '[:lower:]'`

echo "Solution S3 location will be configured to this repo name: $solution_name"
echo "Please provide the solution ID (e.g. SO0xyz):"
read solution_id
echo "Please provide a solution name for the README.md file:"
read readme_name
echo "Please provide an initial description for the README.md file:"
read solution_description

# Update CONTRIBUTING.md from $solution_name
replace="s/%%SOLUTION_NAME%%/$solution_name/g"
echo "sed -i '' -e $replace CONTRIBUTING.md"
sed -i '' -e $replace CONTRIBUTING.md

# Update build-s3-dist.sh with $solution_id
replace="s/%%SOLUTION_ID_VAL%%/$solution_id/g"
echo "sed -i '' -e '$replace' deployment/build-s3-dist.sh"
sed -i '' -e "$replace" deployment/build-s3-dist.sh

# Rename example.yaml to $solution_name.yaml
mv deployment/example.yaml deployment/$solution_name.yaml

# Update README.md solution name with $readme_name
replace="s/%%SOLUTION_NAME%%/$readme_name/g"
echo "sed -i '' -e '$replace' README.md"
sed -i '' -e "$replace" README.md

# Update NOTICE.txt from $solution_name
echo "sed -i '' -e $replace NOTICE.txt"
sed -i '' -e "$replace" NOTICE.txt

# Update README.md description with $solution_description
replace="s/%%SOLUTION_DESCRIPTION%%/$solution_description/g"
echo "sed -i '' -e '$replace' README.md"
sed -i '' -e "$replace" README.md

# Remove TODO.md
rm TODO.md

# Remove copy-repo.sh script
rm copy-repo.sh

# Remove this initalization script
rm initialize-repo.sh
