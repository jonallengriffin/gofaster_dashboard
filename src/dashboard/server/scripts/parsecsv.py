#!/usr/bin/python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Mozilla GoFaster Dashboard.
#
# The Initial Developer of the Original Code is
# Mozilla foundation
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   William Lachance <wlachance@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
    buildevents = sorted(filter(lambda e: e['uid'] == uid, events), key=lambda e: e['finish_time'])

    revision = buildevents[0]['revision']
    submitted_at = buildevents[0]['submitted_at']
    time_taken = (max(map(lambda e: e['finish_time'], buildevents)) - 
                  min(map(lambda e: e['start_time'], buildevents)))
    last_event = buildevents[-1]

    summaries.append({ 'revision': revision, 'uid': uid, 
                       'submitted_at': submitted_at,
                       'time_taken': time_taken,
                       'last_event': last_event })

pickle.dump({'events': events, 'summaries': summaries }, open(sys.argv[2], 'wb'))
