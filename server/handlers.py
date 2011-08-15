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

try:
  import json
except:
  import simplejson as json

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

#Converts datasource formatted time (stopwatch format "x days, 0:00:00") to seconds
def to_seconds(stopwatch_time):
    if str(stopwatch_time).find("day") != -1:
        days = str(stopwatch_time).split(", ")[0].split(" ")[0]
        days = int(days)
        stopwatch_time = str(stopwatch_time).split(", ")[1]
    else:
        days = 0
    split_time = str(stopwatch_time).split(":")
    hours = int(split_time[0])
    minutes = int(split_time[1])
    seconds = int(split_time[2])
    total_seconds = seconds + minutes * 60 + hours * 60 * 60 + days * 60 * 60 * 24
    return int(total_seconds)

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

#Turnaround handler returns total test runtime in seconds and the number of tests for each kind
class TurnaroundHandler(templeton.handlers.JsonHandler):
    def _GET(self, params, body):
        target_os = "all"
        try:
            target_os = params["os"][0]
        except:
            pass

        #Parse csv into well-formatted JSON -- data for turnaround graph
        f = open( '../html/data/buildfaster.csv', 'r' )
        reader = csv.DictReader(f, fieldnames = ( "submitted_at", "revision", "os", "jobtype", "uid", "results", "wait_time", "start_time", "finish_time", "elapsed", "work_time" ) )
        entries = [ row for row in reader ]
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for entry in entries:
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

            # Loop through all entries, calculate averages per day
            (buildtype, jobtype) = entry["jobtype"].split(" ")
            datapoint_date = dateutil.parser.parse(entry["submitted_at"]).strftime("%Y-%m-%d")
            datapoint_os = entry["os"]

            entry["wait_time"] = to_seconds(entry["wait_time"])
            entry["elapsed"] = to_seconds(entry["elapsed"])

            datapoint_type = "_".join([buildtype,jobtype])
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

        #Parse csv into well-formatted JSON -- data for turnaround graph
        f = open( '../html/data/buildfaster.csv', 'r' )
        reader = csv.DictReader(f, fieldnames = ( "submitted_at", "revision", "os", "jobtype", "uid", "results", "wait_time", "start_time", "finish_time", "elapsed", "work_time" ) )
        json_result = json.dumps( [ row for row in reader ] )
        #print json_result

        #Deserialize the JSON to get a usable object
        deserialized = json.loads(json_result)
        #avg = {}
        #return_data = {}
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for x in deserialized:
            #Loop through all entries, calculate averages per day
            jobtype = x["jobtype"].split(" ")
            d = dateutil.parser.parse(x["submitted_at"])
            datapoint_date = d.strftime("%Y-%m-%d")
            datapoint_os = x["os"]

            x["work_time"] = to_seconds(x["work_time"])

            try:
                jobtype[1] #Talos will except on this...
            except:
                continue;

            if jobtype[1] == "test":
                if(show_type == "all" or show_type == "test"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_test"] += x["work_time"]
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_test_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_test"] += x["work_time"]
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_test_counter"] += 1
            elif jobtype[1] == "build":
                if(show_type == "all" or show_type == "build"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_build"] += x["work_time"]
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_build_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_build"] += x["work_time"]
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_build_counter"] += 1

        #return json_result
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

        #Parse csv into well-formatted JSON -- data for turnaround graph
        f = open( '../html/data/buildfaster.csv', 'r' )
        reader = csv.DictReader(f, fieldnames = ( "submitted_at", "revision", "os", "jobtype", "uid", "results", "wait_time", "start_time", "finish_time", "elapsed", "work_time" ) )
        json_result = json.dumps( [ row for row in reader ] )
        #print json_result

        #Deserialize the JSON to get a usable object
        deserialized = json.loads(json_result)
        #avg = {}
        #return_data = {}
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for x in deserialized:
            #Loop through all entries, calculate averages per day
            jobtype = x["jobtype"].split(" ")
            d = dateutil.parser.parse(x["submitted_at"])
            datapoint_date = d.strftime("%Y-%m-%d")
            datapoint_os = x["os"]

            x["wait_time"] = to_seconds(x["wait_time"])

            try:
                jobtype[1] #Talos will except on this...
            except:
                continue;

            if jobtype[1] == "test":
                if(show_type == "all" or show_type == "test"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_test"] += x["wait_time"]
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_test_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_test"] += x["wait_time"]
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_test_counter"] += 1
            elif jobtype[1] == "build":
                if(show_type == "all" or show_type == "build"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_build"] += x["wait_time"]
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_build_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_build"] += x["wait_time"]
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_build_counter"] += 1

        #return json_result
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

        #Parse csv into well-formatted JSON -- data for turnaround graph
        f = open( '../html/data/buildfaster.csv', 'r' )
        reader = csv.DictReader(f, fieldnames = ( "submitted_at", "revision", "os", "jobtype", "uid", "results", "wait_time", "start_time", "finish_time", "elapsed", "work_time" ) )
        json_result = json.dumps( [ row for row in reader ] )
        #print json_result

        #Deserialize the JSON to get a usable object
        deserialized = json.loads(json_result)
        #avg = {}
        #return_data = {}
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for x in deserialized:
            #Loop through all entries, calculate averages per day
            jobtype = x["jobtype"].split(" ")
            d = dateutil.parser.parse(x["submitted_at"])
            datapoint_date = d.strftime("%Y-%m-%d")
            datapoint_os = x["os"]

            #setup and teardown time is just elapsed_time - work_time
            s1s2 = to_seconds(x["elapsed"]) - to_seconds(x["work_time"])

            try:
                jobtype[1] #Talos will except on this...
            except:
                continue;

            if jobtype[1] == "test":
                if(show_type == "all" or show_type == "test"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_test"] += s1s2
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_test_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_test"] += s1s2
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_test_counter"] += 1
            elif jobtype[1] == "build":
                if(show_type == "all" or show_type == "build"):
                    if jobtype[0] == "opt":
                        #tw = wait_time
                        return_data[datapoint_os][datapoint_date]["opt_build"] += s1s2
                        #s1+ta+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["opt_build_counter"] += 1
                    elif jobtype[0] == "debug":
                        #bw = wait_time
                        return_data[datapoint_os][datapoint_date]["dbg_build"] += s1s2
                        #s1+ba+s2 = elapsed_time
                        return_data[datapoint_os][datapoint_date]["dbg_build_counter"] += 1

        #return json_result
        return return_data

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

  #Keeping this for example purposes
  '/test/?', "Test"
)
