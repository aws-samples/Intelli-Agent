#!/bin/bash
#--------------------------------------------------------------------
# Usage: this script must exit with a non-zero return code if the 
# Viperlight scan fails.
#--------------------------------------------------------------------

source_dir='./source'   # May need to adjust this for your repo, but this 
                        # should generally work
viperlight_temp=/tmp/viperlight_scan # should work in most environments
export PATH=$PATH:../viperlight/bin

failed_scans=0

if [ -d $viperlight_temp ]; then
    rm $viperlight_temp/*
    rmdir $viperlight_temp
fi
viperlight_temp=/tmp/viperlight_scan
mkdir $viperlight_temp

scan_npm() {
    echo -----------------------------------------------------------
    echo NPM Scanning $1
    echo -----------------------------------------------------------
    folder_path=`dirname $1`
    viperlight scan -t $folder_path -m node-npmaudit -m node-npmoutdated
    rc=$?
    if [ $rc -eq 0 ]; then
        echo SUCCESS
    elif [ $rc -eq 42 ]; then
        echo NOTHING TO SCAN
    else
        echo FAILED rc=$rc
        ((failed_scans=failed_scans+1))
    fi
}

scan_py() {
    echo -----------------------------------------------------------
    echo Python Scanning $1
    echo -----------------------------------------------------------
    folder_path=`dirname $1`
    viperlight scan -t $folder_path -m python-piprot -m python-safety
    rc=$?
    if [ $rc -eq 0 ]; then
        echo SUCCESS
    elif [ $rc -eq 42 ]; then
        echo NOTHING TO SCAN
    else
        echo FAILED rc=$rc
        ((failed_scans=failed_scans+1))
    fi
}

echo -----------------------------------------------------------
echo Environment
echo -----------------------------------------------------------
echo npm `npm --version`
echo `python --version`

echo -----------------------------------------------------------
echo Update npm to latest
echo -----------------------------------------------------------
npm install -g npm@latest

echo -----------------------------------------------------------
echo Scanning all Nodejs projects
echo -----------------------------------------------------------
find $source_dir -name package.json | grep -v node_modules | while read folder
    do
        echo $folder >> $viperlight_temp/scan_npm_list.txt
    done
while read folder
    do
        scan_npm $folder
    done < $viperlight_temp/scan_npm_list.txt

echo -----------------------------------------------------------
echo Scanning all python projects
echo -----------------------------------------------------------
find . -name requirements.txt | while read folder
    do
        echo $folder >> $viperlight_temp/scan_python_list.txt
    done

while read folder
    do
        if [[ -z $pi_scans_installed ]]; then
            echo Installing piprot and safety
            pip install piprot safety
            pi_scans_installed=YES
        fi
        scan_py $folder
    done < $viperlight_temp/scan_python_list.txt

echo -----------------------------------------------------------
echo Scanning everywhere else
echo -----------------------------------------------------------
viperlight scan
rc=$?
if [ $rc -gt 0 ]; then
    ((failed_scans=failed_scans+1))
fi

if [ $failed_scans == 0 ]
then
    echo Scan completed successfully
else
    echo $failed_scans scans failed. Check previous messages for findings.
fi

exit $failed_scans
