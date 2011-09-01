#!/bin/sh

set -e

SERVER_DIR=$(dirname $0)/../src/dashboard/server/
cd $SERVER_DIR && ../../../bin/python server.py
