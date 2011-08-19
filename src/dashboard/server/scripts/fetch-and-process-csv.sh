#!/bin/sh

set -e

SCRIPT_DIR=$(dirname $0)
DATA_DIR=$(dirname $0)/../data
CSV_OUTPUT=$DATA_DIR/buildfaster.csv
PKL_OUTPUT=$DATA_DIR/buildfaster.pkl

wget http://build.mozilla.org/builds/buildfaster.csv.gz -O - | gunzip > $CSV_OUTPUT
python $SCRIPT_DIR/parsecsv.py $CSV_OUTPUT $PKL_OUTPUT
