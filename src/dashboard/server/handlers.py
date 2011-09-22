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
#   Jonathan Griffin <jgriffin@mozilla.com>
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
from statlib import stats
import stat
import itbf.queue

config = ConfigParser.ConfigParser()
config.read("settings.cfg")
ES_SERVER = config.get("database", "ES_SERVER")

#This line is for if you want to use server-side templates, shouldn't be necessary
render = web.template.render('../templates')

# Get YYYY-MM-DD from unix time (seconds since 1970)
def get_datestr(unixtime):
    return datetime.fromtimestamp(unixtime).strftime('%Y-%m-%d')

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

def get_build_events(range):
    events = get_build_data()['events']
    if range > 0:
        events = filter(lambda e: (datetime.today() - datetime.fromtimestamp(e['submitted_at'])).days < range,
                        events)
    return events

def get_build_summaries():
    return get_build_data()['summaries']

def get_build_jobs():
    return get_build_data()['build_jobs']

def get_mean_times(data, buildtype, include_outliers):
    return_data = defaultdict(lambda: defaultdict(float))
    all_times = reduce(lambda x,y: x+y, reduce(lambda x,y: x+y, map(lambda d: d.values(), data.values())))
    overall_mean = stats.mean(all_times)
    overall_stdev = stats.stdev(all_times)
    for (date, dateval) in data.iteritems():
        typedict = {}
        for (type, times) in dateval.iteritems():
            mean = stats.mean(times)
            if not include_outliers and len(times) > 1:
                included_values = []
                for time in times:
                    if abs(time - overall_mean) < 1.5*overall_stdev:
                        included_values.append(time)
                if len(included_values) > 0:
                    mean = stats.mean(included_values)
                else:
                    mean = None
            typedict[type] = mean
        if buildtype == "maximum" and max(typedict.values()):
            return_data[date] = max(typedict.values())
        elif typedict.get(buildtype):
            return_data[date] = typedict.get(buildtype, 0)

    return return_data

class EndToEndTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self, mode):
        params, body = templeton.handlers.get_request_parms()
        try:
            range = int(params["range"][0])
        except:
            range = 0
        try:
            include_outliers = int(params["include_outliers"][0])
        except:
            include_outliers = 0

        summaries = get_build_summaries()

        # only get summaries in range
        if range > 0:
            summaries = filter(lambda s: (datetime.today() - datetime.fromtimestamp(s['submitted_at'])).days < range,
                               summaries)

        # filter out all but the first build summary per revision
        filtered_summaries = []
        revisions_processed = {}
        for summary in summaries:
            rev = summary['revision'][0:12] # sometimes we only have first 12 chars
            if not revisions_processed.get(rev):
                filtered_summaries.append(summary)
                revisions_processed[rev] = 1
        summaries = filtered_summaries

        if mode == "per_os":
            items = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))
            for os in set(sum(map(lambda s: s['time_taken_per_os'].keys(), 
                                  summaries), [])):
                for date in sorted(set(map(lambda s: get_datestr(s['submitted_at']), summaries))):
                    for summary in filter(lambda s: get_datestr(s['submitted_at'])==date, summaries):
                        if summary['time_taken_per_os'].get(os):
                            items[os][date]["both"].append(summary['time_taken_per_os'][os])

            return_data = {}
            for (os, osval) in items.iteritems():
                return_data[os] = get_mean_times(osval, "both", include_outliers)

            return return_data
        else:
            items = defaultdict(lambda: defaultdict(lambda: []))
            end_to_end_times = []
            for date in sorted(set(map(lambda s: get_datestr(s['submitted_at']), summaries))):
                for summary in filter(lambda s: get_datestr(s['submitted_at'])==date, summaries):
                    items[date]["both"].append(summary['time_taken_overall'])

            return { 'all': get_mean_times(items, "both", include_outliers) }

#Execution Time handler returns average execution time for builds and tests
class ExecutionTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self, type):
        params, body = templeton.handlers.get_request_parms()
        try:
            range = int(params["range"][0])
        except:
            range = 0
        try:
            include_outliers = int(params["include_outliers"][0])
        except:
            include_outliers = 0
        try:
            buildtype = params["buildtype"][0]
        except:
            buildtype = "maximum"

        items = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))
        for event in get_build_events(range):
            # Skip talos
            if event["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(event["submitted_at"])
            datapoint_os = event["os"]
            datapoint_type = "%s_%s" % (event["buildtype"], event["jobtype"])

            if type == "all" or type==event["jobtype"]:
                items[datapoint_os][datapoint_date][datapoint_type].append(event["work_time"])

        return_data = {}
        for (os, osval) in items.iteritems():
            return_data[os] = get_mean_times(osval, buildtype, include_outliers)

        return return_data

#WaitTime handler returns total test runtime in seconds and the number of tests for each kind
class WaitTimeHandler(object):

    @templeton.handlers.json_response
    def GET(self, type):
        params, body = templeton.handlers.get_request_parms()

        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            include_outliers = int(params["include_outliers"][0])
        except:
            include_outliers = 0
        try:
            range = int(params["range"][0])
        except:
            range = 0

        items = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))
        for entry in get_build_events(range):
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            datapoint_type = "all" # don't care about opt vs. debug for wait

            if type == "all" or type==entry["jobtype"]:
                items[datapoint_os][datapoint_date][datapoint_type].append(entry["wait_time"])

        return_data = {}
        for (os, osval) in items.iteritems():
            return_data[os] = get_mean_times(osval, "all", include_outliers)

        return return_data

#Overheadhandler returns setup and teardown times for build, test, or combined
class OverheadHandler(object):

    @templeton.handlers.json_response
    def GET(self, type):
        params, body = templeton.handlers.get_request_parms()

        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            include_outliers = int(params["include_outliers"][0])
        except:
            include_outliers = 0
        try:
            range = int(params["range"][0])
        except:
            range = 0

        items = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))
        for entry in get_build_events(range):
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = get_datestr(entry["submitted_at"])
            datapoint_os = entry["os"]
            datapoint_type = "all" # don't care about opt vs. debug for this

            if type == "all" or type==entry["jobtype"]:
                #setup and teardown time is just elapsed_time - work_time
                s1s2 = entry["elapsed"] - entry["work_time"]
                items[datapoint_os][datapoint_date][datapoint_type].append(s1s2)

        return_data = {}
        for (os, osval) in items.iteritems():
            return_data[os] = get_mean_times(osval, "all", include_outliers)

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
            revision = summary['revision'][0:12]
            if not summaries.get(revision):
                summaries[revision] = []
            summaries[revision].append({'uid': summary['uid'], 
                                        'date': get_datestr(summary['submitted_at']),
                                        'submitted_at': summary['submitted_at'],
                                        'revision': revision,
                                        'time_taken': '{0:1.2f}'.format(summary['time_taken_overall']/60.0/60),
                                        'last_job': summary['last_event']['description']})
       

        result = {}
        for revision in summaries.keys():
            summaries[revision].sort(key=lambda s: s['submitted_at'])
            date = summaries[revision][0]['date']
            if date not in result:
                result[date] = []
            result[date].append({'revision': revision, 'commits': summaries[revision]})

        return map(lambda x: { 'date': x, 'builds': result[x] }, reversed(sorted(result.keys())))

class BuildHandler(object):

    @templeton.handlers.json_response
    def GET(self, buildid):
        params, body = templeton.handlers.get_request_parms()

        summary = filter(lambda s: s['uid'] == buildid, get_build_summaries())[0]
        events = sorted(filter(lambda e: e['uid'] == buildid, get_build_events(0)), 
                             key=lambda e: e['start_time'])

        return { 'summary': summary, 'events': events }

def get_buildjob_detail(revision, slave, buildername):
  if '\"' not in slave:
    slave = '\"%s\"' % slave
  es = ESLib(ES_SERVER, 'logs', 'buildlogs')
  results = es.query({'revision': '%s*' % revision[0:12], 'machine': slave})
  if len(results) == 1:
    return results[0]
  if len(results) > 1:
    for result in results:
      if result['buildername'] == buildername:
        return result
  else:
    return None

class BuildJobHandler(object):

    @templeton.handlers.json_response
    def GET(self, jobid):
        job = get_build_jobs()[int(jobid)]
        detail = get_buildjob_detail(job['revision'], job['slave_name'],
                                     job['builder_name'])
        if detail:
            # convert to float for client's convenience
            for stepname in detail['steps'].keys():
                detail['steps'][stepname] = float(detail['steps'][stepname])
            detail['total'] = float(detail['total'])
            detail['description'] = job['description']
            return detail

        return None

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
  '/endtoendtimes/(average|per_os)/?', "EndToEndTimeHandler",
  '/waittime/(build|test)/?', "WaitTimeHandler",
  '/overhead/(build|test)/?', "OverheadHandler",
  '/executiontime/(build|test)/?', "ExecutionTimeHandler",
  '/builds/?', "BuildsHandler",
  '/builds/([A-z0-9]+)/?', "BuildHandler",
  '/buildjobs/([0-9]+)/?', "BuildJobHandler",
  '/itbf/jobs/?', "IsThisBuildFasterJobsHandler",
)
