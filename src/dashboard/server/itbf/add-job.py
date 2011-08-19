#!/usr/bin/python

# Stupid test script to manually add an "is this build faster" job

import os
import sys
import queue

if len(sys.argv) < 5:
    print "Usage: %s <tree> <revision> <submitter> <return email>" % os.path.basename(sys.argv[0])
    exit(1)

queue.append_job(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
