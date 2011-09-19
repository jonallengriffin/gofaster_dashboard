#!/bin/bash

set -e

export PATH=$(dirname $0):$PATH

SCRIPT_DIR=$(dirname $0)/../src/dashboard/server/scripts/
DATA_DIR=$(dirname $0)/../src/dashboard/server/data/
CSV_OUTPUT=$DATA_DIR/buildfaster.csv
PKL_OUTPUT=$DATA_DIR/buildfaster.pkl
LOCAL=0

while getopts l OPTION; do
    case $OPTION in
        l) LOCAL=1 ;;
       \?) echo "Usage: $0 [ -l ]" && exit 2;;
    esac
done

if [ $LOCAL == 0 ]; then
    wget http://build.mozilla.org/builds/buildfaster.csv.gz -O - | gunzip > $CSV_OUTPUT
fi
python $SCRIPT_DIR/parsecsv.py $CSV_OUTPUT $PKL_OUTPUT
