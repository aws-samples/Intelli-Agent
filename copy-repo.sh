#!/bin/bash
echo "Path to repo to copy to (e.g. ../new-solution-name): "
read solution_path
echo "Initialize repo (y/n)? [N]:"
read init_repo
if [ .$init_repo = "." ]; then
	init_repo="n"
fi
init_repo=$(echo $init_repo | tr '[:upper:]' '[:lower:]')

cp -r * $solution_path
mkdir -p $solution_path/.github
cp -r .github/* $solution_path/.github/
cp .gitignore $solution_path
cp .viperlight* $solution_path

echo "Viperlight: enter 'y' to use the custom codescan script, codescan-prebuild-custom.sh:"
echo -e "- runs python scans where there is a requirements.txt"
echo -e "- updates environment to npm@latest (regardless of whether npm is used)"
echo -e "- runs node scans where there is a package.json"
echo -e "- runs viperlight scan from the root"
echo -e "\nInstall codescan-prebuild-custom.sh (y/n)? [Y]:"
read use_custom_script
if [ .$use_custom_script = "." ]; then
	use_custom_script="y"
fi
use_custom_script=$(echo $use_custom_script | tr '[:upper:]' '[:lower:]')

if [ $use_custom_script = "y" ]; then
	cp codescan-prebuild-custom.sh $solution_path
	chmod +x $solution_path/codescan-prebuild-custom.sh
fi

if [ $init_repo = "y" ]; then
  cd $solution_path
  chmod +x initialize-repo.sh
  ./initialize-repo.sh
fi
