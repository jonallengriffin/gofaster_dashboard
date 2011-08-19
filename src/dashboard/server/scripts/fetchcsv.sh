#!/bin/sh

set -e

if [ ! -n "$PYTHON" ]; then
    echo "PYTHON environment variable not set (should be path to python interpreter you want to use)"
    exit 1
fi

SCRIPT_DIR=$(dirname $0)
DATA_DIR=$(dirname $0)/../data
CSV_OUTPUT=$DATA_DIR/buildfaster.csv
PKL_OUTPUT=$DATA_DIR/buildfaster.pkl

wget http://build.mozilla.org/builds/buildfaster.csv.gz -O - | gunzip > $CSV_OUTPUT
$PYTHON $SCRIPT_DIR/parsecsv.py $CSV_OUTPUT $PKL_OUTPUT
