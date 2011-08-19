#!/usr/bin/python

import sys
import csv
import dateutil.parser
import cPickle as pickle
import datetime

# Converts datasource formatted time (stopwatch format "x days, 0:00:00") to seconds
def to_seconds(stopwatch_time):
    days = 0
    if str(stopwatch_time).find("day") != -1:
        days = int(str(stopwatch_time).split(", ")[0].split(" ")[0])
        stopwatch_time = str(stopwatch_time).split(", ")[1]
    (hours, minutes, seconds) = map(lambda s: int(s), stopwatch_time.split(":"))
    return seconds + minutes * 60 + hours * 60 * 60 + days * 60 * 60 * 24

f = open(sys.argv[1], 'r')
reader = csv.DictReader(f)

entries = []
for row in reader:
    # ignore results > 30 days old
    submitted_at = dateutil.parser.parse(unicode(row["submitted_at"]))
    if (datetime.datetime.today() - submitted_at).days > 30:
        continue

    entry = {}
    entry["submitted_at"] = submitted_at.strftime("%Y-%m-%d")

    if row["jobtype"] == "talos":
        entry['jobtype'] = "talos"
    else:
        (entry['buildtype'], entry['jobtype']) = row["jobtype"].split(" ")

    entry["work_time"] = to_seconds(row["work_time"])
    entry["wait_time"] = to_seconds(row["wait_time"])
    entry["elapsed"] = to_seconds(row["elapsed"])
    entry["os"] = row["os"]

    entries.append(entry)

pickle.dump(entries, open(sys.argv[2], 'wb'))
