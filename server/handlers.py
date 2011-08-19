# handlers.py

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

#Parse csv into well-formatted JSON -- data for turnaround graph
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

#Mochitest handler returns mochitest runtimes on given days and builds
class MochitestHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        #params_array = json.load(str(params))
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
class TurnaroundHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        target_os = "all"
        try:
            target_os = params["os"][0]
        except:
            pass

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_data():
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = entry["submitted_at"]
            datapoint_os = entry["os"]
            if datapoint_os == "win7" or datapoint_os == "winxp":                
                datapoint_os = "win32" # for overall time, win7/winxp tests are win32 datapoints
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"
            
            return_data[datapoint_os][datapoint_date][datapoint_type] += entry["wait_time"]
            return_data[datapoint_os][datapoint_date][datapoint_type] += entry["elapsed"]
            return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

#Execution Time handler returns average execution time for builds and tests
class ExecutionTimeHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        try:
            target_os = params["os"][0]
        except:

            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_data():
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = entry["submitted_at"]
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"

            if show_type == "all" or show_type==entry["jobtype"]:
                return_data[datapoint_os][datapoint_date][datapoint_type] += entry["work_time"]
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

#WaitTime handler returns total test runtime in seconds and the number of tests for each kind
class WaitTimeHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_data():
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = entry["submitted_at"]
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"

            if show_type == "all" or show_type==entry["jobtype"]:
                return_data[datapoint_os][datapoint_date][datapoint_type] += entry["wait_time"]
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

#Overheadhandler returns setup and teardown times for build, test, or combined
class OverheadHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        try:
            target_os = params["os"][0]
        except:
            target_os = "all"
        try:
            show_type = params["type"][0]
        except:
            show_type = "all"

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for entry in get_build_data():
            if entry["jobtype"] == "talos":
                continue

            datapoint_date = entry["submitted_at"]
            datapoint_os = entry["os"]
            datapoint_type = "%s_%s" % (entry["buildtype"], entry["jobtype"])
            datapoint_counter = datapoint_type + "_counter"
            
            if show_type == "all" or show_type==entry["jobtype"]:
                #setup and teardown time is just elapsed_time - work_time
                s1s2 = entry["elapsed"] - entry["work_time"]
                return_data[datapoint_os][datapoint_date][datapoint_type] += s1s2
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

        return return_data

class IsThisBuildFasterJobsHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        return { 'num_pending_jobs': len(itbf.queue.get_copy()) }

    @templeton.handlers.get_json
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

#Example non-json Handler
class Test:
    def GET(self):
        return render.test('treebark')

# URLs go here. "/api/" will be automatically prepended to each.
urls = (
  '/mochitest/?', "MochitestHandler",
  '/turnaround/?', "TurnaroundHandler",
  '/waittime/?', "WaitTimeHandler",
  '/overhead/?', "OverheadHandler",
  '/executiontime/?', "ExecutionTimeHandler",
  '/itbf/jobs/?', "IsThisBuildFasterJobsHandler",

  #Keeping this for example purposes
  '/test/?', "Test"
)
