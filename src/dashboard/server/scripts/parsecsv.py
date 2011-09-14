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

from collections import defaultdict
import re
import sys
import csv
import dateutil.parser
import cPickle as pickle
import datetime
from time import mktime

builderRe = re.compile(r'(Rev3 )?(.*?)mozilla-central (.*)')

# Converts datasource formatted time (stopwatch format "x days, 0:00:00") to seconds
def to_seconds(stopwatch_time):
    days = 0
    if str(stopwatch_time).find("day") != -1:
        days = int(str(stopwatch_time).split(", ")[0].split(" ")[0])
        stopwatch_time = str(stopwatch_time).split(", ")[1]
    (hours, minutes, seconds) = map(lambda s: int(s), stopwatch_time.split(":"))
    return seconds + minutes * 60 + hours * 60 * 60 + days * 60 * 60 * 24

def suite_event_key(row):
    return "".join([row["uid"],row["suitename"],row["jobtype"],row["os"]])

f = open(sys.argv[1], 'r')
reader = csv.DictReader(f)

events = []
suite_events = defaultdict(lambda: defaultdict(int))
build_jobs = []

for row in reader:
    # if it has a suitename, only process it if it's the first event for that suite
    # (ignores tests run more than once for nightly builds)
    if len(row['suitename']) > 0 and suite_events[suite_event_key(row)]:
        continue

    event = {}
    event["uid"] = row["uid"]
    event["revision"] = row["revision"]
    event["submitted_at"] = mktime(dateutil.parser.parse(unicode(row["submitted_at"])).timetuple())
    event["start_time"] = mktime(dateutil.parser.parse(unicode(row["start_time"])).timetuple())
    event["finish_time"] = mktime(dateutil.parser.parse(unicode(row["finish_time"])).timetuple())

    if row["jobtype"] == "talos":
        event['jobtype'] = "talos"
    else:
        (event['buildtype'], event['jobtype']) = row["jobtype"].split(" ")

    match = builderRe.match(row["builder_name"])
    # remove 'Rev3' and 'mozilla-central' from the builder name
    if match:
        event["description"] = match.group(2) + match.group(3)
    else:
        event["description"] = row["builder_name"]

    if event['jobtype'] == "build":
        event['build_job_id'] = len(build_jobs)
        build_jobs.append({ 'revision': event['revision'],
                            'builder_name': row['builder_name'],
                            'slave_name': row['slave_name'],
                            'description': event['description']
                            })

    if len(row['suitename']) > 0:
        event['suitename'] = row['suitename']
        suite_events[suite_event_key(row)] = 1

    event["work_time"] = to_seconds(row["work_time"])
    event["wait_time"] = to_seconds(row["wait_time"])
    event["elapsed"] = to_seconds(row["elapsed"])
    event["os"] = row["os"]

    events.append(event)

summaries = []
for uid in set(map(lambda e: e["uid"], events)):
    events_for_build = sorted(filter(lambda e: e['uid'] == uid, events), key=lambda e: e['finish_time'])

    revision = events_for_build[0]['revision']
    submitted_at = events_for_build[0]['submitted_at']
    last_event = events_for_build[-1]

    time_taken_per_os = {}
    def get_time_taken(events_for_build):
        return (max(map(lambda e: e['finish_time'], events_for_build)) - 
                min(map(lambda e: e['start_time'], events_for_build)))
    for os in set(map(lambda e: e['os'], events_for_build)):
        if os == 'win32':
            # win32 is just the build component, where we want end to end
            continue
        elif os == "win7" or os == "winxp":
            # for overall time, win7/winxp incorporates win32 build times
            os_events_for_build = filter(lambda e: e['os']==os or e['os']=='win32', 
                                         events_for_build)
        else:
            os_events_for_build = filter(lambda e: e['os']==os, events_for_build)
        time_taken_per_os[os] = get_time_taken(os_events_for_build)        
    time_taken_overall = get_time_taken(events_for_build)

    summaries.append({ 'revision': revision, 'uid': uid, 
                       'submitted_at': submitted_at,
                       'time_taken_per_os': time_taken_per_os,
                       'time_taken_overall': time_taken_overall,
                       'last_event': last_event })

pickle.dump({'events': events, 'summaries': summaries, 'build_jobs': build_jobs }, open(sys.argv[2], 'wb'))
