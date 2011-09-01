#!/bin/bash

set -e

export PATH=$(dirname $0):$PATH

SCRIPT_DIR=$(dirname $0)/../src/dashboard/server/scripts/
DATA_DIR=$(dirname $0)/../src/dashboard/server/data/
CSV_OUTPUT=$DATA_DIR/buildfaster.csv
PKL_OUTPUT=$DATA_DIR/buildfaster.pkl

wget http://build.mozilla.org/builds/buildfaster.csv.gz -O - | gunzip > $CSV_OUTPUT
python $SCRIPT_DIR/parsecsv.py $CSV_OUTPUT $PKL_OUTPUT
