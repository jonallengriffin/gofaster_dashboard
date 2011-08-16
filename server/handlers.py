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
    days = 0
    if str(stopwatch_time).find("day") != -1:
        days = int(str(stopwatch_time).split(", ")[0].split(" ")[0])
        stopwatch_time = str(stopwatch_time).split(", ")[1]
    (hours, minutes, seconds) = map(lambda s: int(s), stopwatch_time.split(":"))
    return seconds + minutes * 60 + hours * 60 * 60 + days * 60 * 60 * 24

#Parse csv into well-formatted JSON -- data for turnaround graph
def parse_build_csv():
    f = open( '../html/data/buildfaster.csv', 'r' )
    reader = csv.DictReader(f, fieldnames = ( "submitted_at", "revision", "os", "jobtype", "uid", "results", "wait_time", "start_time", "finish_time", "elapsed", "work_time" ) )
    return [ row for row in reader ]


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

        entries = parse_build_csv()
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for entry in entries:
            # Skip talos
            if entry["jobtype"] == "talos":
                continue

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

        entries = parse_build_csv()

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for entry in entries:
            if entry["jobtype"] == "talos":
                continue

            (buildtype, jobtype) = entry["jobtype"].split(" ")

            datapoint_os = entry["os"]
            datapoint_type = "_".join([buildtype,jobtype])
            datapoint_counter = datapoint_type + "_counter"
            datapoint_date = dateutil.parser.parse(entry["submitted_at"]).strftime("%Y-%m-%d")

            if show_type == "all" or show_type==jobtype:
                return_data[datapoint_os][datapoint_date][datapoint_type] += to_seconds(entry["work_time"])
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

        entries = parse_build_csv()

        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for entry in entries:
            if entry["jobtype"] == "talos":
                continue

            (buildtype, jobtype) = entry["jobtype"].split(" ")

            datapoint_date = dateutil.parser.parse(entry["submitted_at"]).strftime("%Y-%m-%d")
            datapoint_os = entry["os"]
            datapoint_type = "_".join([buildtype,jobtype])
            datapoint_counter = datapoint_type + "_counter"

            if show_type == "all" or show_type==jobtype:
                return_data[datapoint_os][datapoint_date][datapoint_type] += to_seconds(entry["wait_time"])
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

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

        entries = parse_build_csv()
        return_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for entry in entries:
            if entry["jobtype"] == "talos":
                continue

            (buildtype, jobtype) = entry["jobtype"].split(" ")

            datapoint_os = entry["os"]
            datapoint_type = "_".join([buildtype,jobtype])
            datapoint_counter = datapoint_type + "_counter"
            datapoint_date = dateutil.parser.parse(entry["submitted_at"]).strftime("%Y-%m-%d")
            
            if show_type == "all" or show_type==jobtype:
                #setup and teardown time is just elapsed_time - work_time
                s1s2 = to_seconds(entry["elapsed"]) - to_seconds(entry["work_time"])
                return_data[datapoint_os][datapoint_date][datapoint_type] += s1s2
                return_data[datapoint_os][datapoint_date][datapoint_counter] += 1

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
