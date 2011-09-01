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
#   Sam Liu <sam@ambushnetworks.com>
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
from datetime import date, datetime, time, timedelta
from decimal import *
from mozautoeslib import ESLib
import ConfigParser
import csv
import dateutil.parser
import io
import re
import templeton
import web
import time
import os.path
import cPickle as pickle
import stat
import itbf.queue

config = ConfigParser.ConfigParser()
config.read("settings.cfg")
ES_SERVER = config.get("database", "ES_SERVER")
eslib = ESLib(ES_SERVER, config.get("database", "INDEX"), config.get("database", "TYPE"))

#This line is for if you want to use server-side templates, shouldn't be necessary
render = web.template.render('../templates')

#Example MySQL Query
#db = web.database(dbn='mysql', db='dbname', user='user', pw='password')
#results = db.query("SELECT * FROM steps limit 1")

# Get YYYY-MM-DD from unix time (seconds since 1970)
def get_datestr(unixtime):
    return datetime.fromtimestamp(unixtime).strftime('%Y-%m-%d')

# Gets dates from parameters and parses to correct format
# Returns tuple with startdate and enddate parsed from URL string
def get_dates(params, days_apart=7):
    startdate = None
    enddate = None
    try:
        startdate = params["startdate"][0]
        startdate = re.search(r'(\d\d\d\d-\d\d-\d\d)',startdate).group(0)
        startdate = datetime.strptime(str(startdate), "%Y-%m-%d")
       #Check that startdate is an isoformat date string
    except:
        pass
    try:
        enddate = params["enddate"][0]
        enddate = re.search(r'(\d\d\d\d-\d\d-\d\d)',enddate).group(0)
        enddate = datetime.strptime(str(enddate), "%Y-%m-%d")
        #Check that startdate is an isoformat date string
    except:
        pass

    if startdate is None:
        startdate = datetime.today()
    if enddate is None and startdate != None:
        delta = timedelta(days=days_apart)
        enddate = startdate - delta
    startdate = startdate.strftime("%Y-%m-%d")
    enddate = enddate.strftime("%Y-%m-%d")
    return (startdate, enddate)

last_parsed_buildfaster_data = None
buildfaster_data = None
def get_build_data():
    global last_parsed_buildfaster_data
    global buildfaster_data
    fname = 'data/buildfaster.pkl'
    mtime = os.stat(fname)[stat.ST_MTIME]
    if last_parsed_buildfaster_data != mtime:
        buildfaster_data = pickle.load(open(fname, 'r'))
        last_parsed_buildfaster_data = mtime
    return buildfaster_data

def get_build_events():
    return get_build_data()['events']

def get_build_summaries():
    return get_build_data()['summaries']

#Mochitest handler returns mochitest runtimes on given days and builds
class MochitestHandler(object):
    def GET(self):
        params, body = templeton.handlers.get_request_parms()

        args = {}
        args["date"] = []
        dates = get_dates(params)
        startdate = dates[0]
        enddate = dates[1]
        try:
            params["enddate"][0]
            args["date"].append(startdate)
            args["date"].append(enddate)
        except:
            args["date"] = startdate

        try:
            params["buildtype"][0]
            args["buildtype"] = params["buildtype"][0]
        except:
            pass

        try:
            params["os"][0]
            args["os"] = params["os"][0]
        except:
            pass

        result = eslib.query(args)
        return result

#Turnaround handler returns total build+test runtime in seconds and the number of tests for each kind
class TurnaroundHandler(object):

    @templeton.handlers.json_response
    def GET(self, params, body):
        params, body = templeton.handlers.get_request_parms()

        target_os = "all"
        try:
            target_os = params["os"][0]
        except:
            pass

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_events():
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

            datapoint_os = entry["os"]
            if datapoint_os == "win7" or datapoint_os == "winxp":                
                datapoint_os = "win32" # for overall time, win7/winxp tests are win32 datapoints

            if target_os != "all" and datapoint_os != target_os:
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            if datapoint_os == "win7" or datapoint_os == "winxp":                
                datapoint_os = "win32" # for overall time, win7/winxp tests are win32 datapoints
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"
            
            return_data[datapoint_os][datapoint_date][datapoint_type] += entry["wait_time"]
            return_data[datapoint_os][datapoint_date][datapoint_type] += entry["elapsed"]
            return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

class EndToEndTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        params, body = templeton.handlers.get_request_parms()
        try:
            mode = params["mode"][0]
        except:
            mode = "average"
        print mode
        summaries = get_build_summaries()

        if mode == "os":
            end_to_end_times = defaultdict(lambda: [])
            for os in set(sum(map(lambda s: s['time_taken_per_os'].keys(), 
                                  summaries), [])):
                for date in sorted(set(map(lambda s: get_datestr(s['submitted_at']), summaries))):
                    count = 0.0
                    total = 0
                    for summary in filter(lambda s: get_datestr(s['submitted_at'])==date, summaries):
                        if summary['time_taken_per_os'].get(os):
                            total += summary['time_taken_per_os'][os]
                            count += 1
                    end_to_end_times[os].append([date, total/count])

            return { 'end_to_end_times': end_to_end_times }


        end_to_end_times = []
        for date in sorted(set(map(lambda s: get_datestr(s['submitted_at']), summaries))):
            count = 0.0
            total = 0
            for summary in filter(lambda s: get_datestr(s['submitted_at'])==date, summaries):
                total += summary['time_taken_overall']
                count += 1
            end_to_end_times.append([date, total/count])
                
        return { 'end_to_end_times': end_to_end_times }

#Execution Time handler returns average execution time for builds and tests
class ExecutionTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        params, body = templeton.handlers.get_request_parms()

        try:
            target_os = params["os"][0]
        except:

            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_events():
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"

            if show_type == "all" or show_type==entry["jobtype"]:
                return_data[datapoint_os][datapoint_date][datapoint_type] += entry["work_time"]
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

#WaitTime handler returns total test runtime in seconds and the number of tests for each kind
class WaitTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        params, body = templeton.handlers.get_request_parms()

        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_events():
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"

            if show_type == "all" or show_type==entry["jobtype"]:
                return_data[datapoint_os][datapoint_date][datapoint_type] += entry["wait_time"]
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

#Overheadhandler returns setup and teardown times for build, test, or combined
class OverheadHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        params, body = templeton.handlers.get_request_parms()

        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_events():
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"
            
            if show_type == "all" or show_type==entry["jobtype"]:
                #setup and teardown time is just elapsed_time - work_time
                s1s2 = entry["elapsed"] - entry["work_time"]
                return_data[datapoint_os][datapoint_date][datapoint_type] += s1s2
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

def get_build_detail(buildid):
    buildevents = sorted(filter(lambda e: e['uid'] == buildid, get_build_events()), 
                         key=lambda e: e['start_time'])
    
    return { 'date': get_datestr(buildevents[0]['submitted_at']),
             'revision': buildevents[0]['revision'][0:8],
             'buildevents': buildevents }

class BuildsHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        summaries = {}
        for summary in get_build_summaries():
            date = get_datestr(summary['submitted_at'])
            if not summaries.get(date):
                summaries[date] = []
            summaries[date].append({'uid': summary['uid'], 
                                    'revision': summary['revision'],
                                    'time_taken': summary['time_taken_overall'],
                                    'last_event': summary['last_event']})
        
        for date in summaries.keys():
            summaries[date].sort(key=lambda s: s['time_taken'])
            summaries[date].reverse()

        return { 'builds': map(lambda b: { 'date': b, 
                                           'builds': summaries[b] }, 
                               reversed(sorted(summaries.keys()))) }

class BuildDataHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        params, body = templeton.handlers.get_request_parms()

        buildid = params["buildid"][0]
        summary = filter(lambda s: s['uid'] == buildid, get_build_summaries())[0]
        events = sorted(filter(lambda e: e['uid'] == buildid, get_build_events()), 
                             key=lambda e: e['start_time'])

        return { 'summary': summary, 'events': events }

class IsThisBuildFasterJobsHandler(object):

    @templeton.handlers.json_response
    def GET(self):
        return { 'num_pending_jobs': len(itbf.queue.get_copy()) }

    @templeton.handlers.json_response
    def POST(self):
        postdata = web.input()

        if len(itbf.queue.get_copy()) > 100:
            # defend against people flooding the queue
            errmsg = "Too many jobs! Geez."
            web.internalerror(message=errmsg)
            return { 'error': errmsg }

        itbf.queue.append_job(postdata['tree'], postdata['revision'], 
                              postdata['submitter_email'], postdata['return_email'])
        return { 'num_pending_jobs': len(itbf.queue.get_copy()) }

# URLs go here. "/api/" will be automatically prepended to each.
urls = (
  '/mochitest/?', "MochitestHandler",
  '/turnaround/?', "TurnaroundHandler",
  '/endtoendtimes/?', "EndToEndTimeHandler",
  '/waittime/?', "WaitTimeHandler",
  '/overhead/?', "OverheadHandler",
  '/executiontime/?', "ExecutionTimeHandler",
  '/builds/?', "BuildsHandler",
  '/builddata/?', "BuildDataHandler",
  '/itbf/jobs/?', "IsThisBuildFasterJobsHandler",
)
