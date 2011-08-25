#!/usr/bin/python

import sys
import csv
import dateutil.parser
import cPickle as pickle
import datetime
from time import mktime

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

events = []
for row in reader:
    # ignore results > 30 days old
    submitted_at = dateutil.parser.parse(unicode(row["submitted_at"]))
    if (datetime.datetime.today() - submitted_at).days > 30:
        continue

    event = {}
    event["uid"] = row["uid"]
    event["revision"] = row["revision"]
    event["submitted_at"] = submitted_at.strftime("%Y-%m-%d")
    event["start_time"] = mktime(dateutil.parser.parse(unicode(row["start_time"])).timetuple())
    event["finish_time"] = mktime(dateutil.parser.parse(unicode(row["finish_time"])).timetuple())

    if row["jobtype"] == "talos":
        event['jobtype'] = "talos"
    else:
        (event['buildtype'], event['jobtype']) = row["jobtype"].split(" ")

    event["work_time"] = to_seconds(row["work_time"])
    event["wait_time"] = to_seconds(row["wait_time"])
    event["elapsed"] = to_seconds(row["elapsed"])
    event["os"] = row["os"]

    events.append(event)

summaries = []
for uid in set(map(lambda e: e["uid"], events)):
    buildevents = filter(lambda e: e['uid'] == uid, events)

    revision = buildevents[0]['revision']
    submitted_at = buildevents[0]['submitted_at']
    time_taken = (max(map(lambda e: e['finish_time'], buildevents)) - 
                  min(map(lambda e: e['start_time'], buildevents)))

    summaries.append({ 'revision': revision, 'uid': uid, 
                       'submitted_at': submitted_at,
                       'time_taken': time_taken })

pickle.dump({'events': events, 'summaries': summaries }, open(sys.argv[2], 'wb'))
