#!/usr/bin/python

# Stupid test script to manually add an "is this build faster" job

import sys
import queue

if len(sys.argv) < 4:
    print "Usage: %prog <tree> <revision> <submitter>"
    exit(1)

queue.append_job(sys.argv[1], sys.argv[2], sys.argv[3])
