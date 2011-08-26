/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is the Mozilla GoFaster Dashboard.
 *
 * The Initial Developer of the Original Code is
 * Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2___
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Sam Liu <sam@ambushnetworks.com>
 *   William Lachance <wlachance@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/*
* graphs.js
*
* @author   Sam Liu <sam@ambushnetworks.com>
* @desc     Internal
* @depends  Jquery
* @notes    Results output to div id "result", graphs
*           draw to "container," all other messages
*           go to "error."
*
*/

function show_loading(){
    //Clear the display divs and show loading gif
  $('#result').html("<div id='loading' style='margin:0 auto; padding-top:20px;'><center><span style='font-weight:200; font-size:200%;'>Loading...</span><br/><img height='32' width='32' src='images/loading.gif' alt='' /></center></div>");
  $('#errors').html("");
  $('#container').hide();
}

function hide_loading(){
    //Hide loading div after page loads
    $('#loading').html("")
}

function sortPairs(a,b){
    //Sort function for array -- used in determining top mochitests
    if(a[0] > b[0]){
        return -1;
    }
    return 1;
}
function rmDupPairs(arr) {
    //Remove duplicates from sorted tuple array (specific to show_mochitests)
    var i;
    len=arr.length;
    out=[];
    obj={};

    //Mark hash table
    for (i=0;i<len;i++) {
        obj[arr[i][1]]=0;
    }

    //Skip over things that are marked duplicate in the hash table
    for (i in arr) {
        if (obj[arr[i][1]] == 0){
            obj[arr[i][1]] = 1;
            out.push(arr[i]);
        }
    }
    return out;
}

function ISODateString(d){
    //Get ISO Date from UTC Date
    function pad(n){return n<10 ? '0'+n : n}
    return d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate());
}
/*
function basename(path) {
    //Gets basename of a path
    return path.replace(/\\/g, '/').replace(/.*\//, '' );
}
*/
function divide(dividend, divisor){
    //Division function that allows division by zero (returns zero)
    quotient = dividend/divisor;
    if(isFinite(quotient)){
        return quotient;
    }
    return 0;
}

function parseDate(datestr) {
  var parsed = datestr.split("-");
  var year = parsed[0];
  var month = parsed[1] - 1; //Javascript months index from 0 instead of 1
  var day = parsed[2];

  return Date.UTC(year, month, day);
}

function to_hours(value){
    //Convert a time from seconds to hours to two decimal places
    return Math.round(value * 100 / 60 / 60) / 100;
}

//Each function below represents a graph to be displayed

function show_turnaround(type) {
  //Build and Test Turnaround Dashboard
  show_loading(); //Show loading div to keep user happy
  
  //Request data from api/turnaround and do stuff
  $.getJSON('api/turnaround', function(data) {

    //Loading is complete!
    hide_loading();
    $('#container').show();

    if (type === "total") {
      $('#result').append("<h3>Go Faster! - Overall Build & Test Turnaround</h3><br/>");

      //Group data by OS
      var graph_data = Object.keys(data).map(function(os) {
        //Save each series into a set for display on the chart
        var series = {};
        series.label = os;
        series.data = Object.keys(data[os]).map(function(datestr) {
          //Calculate datapoint display value
          var dbg_total = divide(data[os][datestr]["debug_build"],
                                 data[os][datestr]["debug_build_counter"]) + 
            divide(data[os][datestr]["debug_test"],
                   data[os][datestr]["debug_test_counter"]);
          
          var opt_total = divide(data[os][datestr]["opt_build"], 
                                 data[os][datestr]["opt_build_counter"]) + 
            divide(data[os][datestr]["opt_test"],
                   data[os][datestr]["opt_test_counter"]);
          
          return [parseDate(datestr), to_hours(Math.max(dbg_total, opt_total))];        
        }).sort(function(a,b) { return a[0]-b[0]; });
        
        return series;
      });

      $.plot($("#container"), graph_data, {
        xaxis: {
          mode: "time"
        },
        yaxis: {
          axisLabel: 'Average Turnaround Time (Hours)'
        },
        series: {
          lines: { show: true, fill: false, steps: false },
          points: { show: true }
        }
      });

    } else { // type == components

      $('#result').append("<h3>Go Faster! - Relative Build & Test Turnaround</h3><select><option>All platforms</option><option>win32</option></select><br/>");

      var graphdata = [];
      var alldates = Object.keys(data).map(function(os) {
        return Object.keys(data[os]);
      }).reduce(function(datearray1,datearray2) { 
        return datearray1.concat(datearray2); 
      }).filter(function(itm,i,a){
        return i==a.indexOf(itm);
      });

      ["build", "test"].forEach(function(action) {
        var series = {};
        series.label = action;
        series.data = alldates.map(function(datestr) {
          //Calculate datapoint display value
          var total = 0;
          Object.keys(data).forEach(function(os) {
            if (data[os][datestr] !== undefined) {
              var debug_total = divide(data[os][datestr]['debug_'+action],
                                       data[os][datestr]['debug_'+action+'_counter']);  
              var opt_total = divide(data[os][datestr]["opt_"+action], 
                                     data[os][datestr]["opt_"+action+"_counter"]);
              total += to_hours(Math.max(debug_total, opt_total));
            }
          });
          
          return [parseDate(datestr), total];
        }).sort(function(a,b) { return a[0]-b[0]; });
        graphdata.push(series);
      });

      $.plot($("#container"), graphdata, {
        xaxis: {
          mode: "time"
        },
        yaxis: {
          axisLabel: 'Cumulative Time (Hours)'
        },
        series: {
          stack: true,
          lines: { show: true, fill: true, steps: false },
        }
      });
      
    }
  });  
}

function show_endtoend() {
  show_loading(); //Show loading div to keep user happy
  
  //Request data from api/turnaround and do stuff
  $.getJSON('api/endtoendtimes', function(data) {
    //Loading is complete!
    hide_loading();
    $('#container').show();

    $('#result').append("<h3>Go Faster! - Average End to End Performance per OS</h3><br/>");    
    //Group data by OS
    var end_to_end_times = data.end_to_end_times;
    var graphdata = Object.keys(end_to_end_times).map(function(os) {
      var series = {};
      series.label = os;
      series.data = end_to_end_times[os].map(function(datapoint) {
          return [parseDate(datapoint[0]), to_hours(datapoint[1])];
      });
      return series;
    });
    
    $.plot($("#container"), graphdata, {
      xaxis: {
        mode: "time"
      },
      yaxis: {
        axisLabel: 'Time (Hours)'
      },
      series: {
        lines: { show: true, fill: false, steps: false },
        points: { show: true }
      },
      legend: {
        position: "nw",
        hideable: true
      }
    });
  });
}

function show_executiontime(params_type){
    //Build and Test Execution Dashboard
    show_loading(); //Show loading div to keep user happy

    //Request data from api/turnaround and do stuff
    if(params_type){
        resourceURL = 'api/executiontime?type='+params_type;
        graph_title = "Average execution times for "+params_type;
    }else{
        resourceURL = 'api/waittime';
        graph_title = "Combined average execution times for build and test";
    }

    $.getJSON(resourceURL, function(data) {
        $('#container').show();
        graph_data = [];

        //Group data by OS
        for (os in data){
            //Save each series into a set for display on the chart
            series = {};
            series.name = os;
            series.data = []
            for(datestr in data[os]){

                //Calculate datapoint display value
                dbg_total = divide(data[os][datestr]["debug_build"],data[os][datestr]["debug_build_counter"]) + divide(data[os][datestr]["debug_test"],data[os][datestr]["debug_test_counter"]);
                opt_total = divide(data[os][datestr]["opt_build"],data[os][datestr]["opt_build_counter"]) + divide(data[os][datestr]["opt_test"],data[os][datestr]["opt_test_counter"]);
                value = Math.max(dbg_total,opt_total);

              //Convert from seconds to hours
              value = to_hours(value);
              
              //Form datapoint
              datapoint = [parseDate(datestr), value];
              
              //Push datapoint to the series
              series['data'].push(datapoint);
            }
            //Push each completed series to the overall dataset
            graph_data.push(series);
        }
        //Loading is complete!
        hide_loading();

        //Begin Line Chart
        var chart;
        jQuery(document).ready(function() {
            chart = new Highcharts.Chart({
                chart: {
                    renderTo: 'container',
                    type: 'spline'
                },
                title: {
                    text: 'Go Faster! - '+graph_title
                },
                subtitle: {
                    text: ''
                },
                xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: { // don't display the dummy year
                        month: '%b %e',
                        year: '%Y'
                    }
                },
                yAxis: {
                    title: {
                        text: 'Average Execution Time (Hours)'
                    },
                    min: 0
                },
                tooltip: {
                    formatter: function() {
                            return '<b>'+ this.series.name +'</b><br/>'+
                            Highcharts.dateFormat('%b %e, %Y', this.x) +': '+ this.y +' hours';
                    }
                },
                series: graph_data
            });
        });
        //End Line Chart
    }); //End $.getJSON
}

function show_waittime(params_type){
    //Build Wait Dashboard
    show_loading(); //Show loading div to keep user happy

    //Request data from api/turnaround and do stuff
    if(params_type){
        resourceURL = 'api/waittime?type='+params_type;
        graph_title = "Average wait times for "+params_type;
    }else{
        resourceURL = 'api/waittime';
        graph_title = "Combined average wait times for build and test";
    }
    $.getJSON(resourceURL, function(data) {
        $('#container').show();

        graph_data = [];

        //Group data by OS
        for (os in data){
            //Save each series into a set for display on the chart
            series = {};
            series.name = os;
            series.data = []
            for(datestr in data[os]){
              //Calculate datapoint display value
              dbg_total = divide(data[os][datestr]["debug_build"],data[os][datestr]["debug_build_counter"]) + divide(data[os][datestr]["debug_test"],data[os][datestr]["debug_test_counter"]);
              opt_total = divide(data[os][datestr]["opt_build"],data[os][datestr]["opt_build_counter"]) + divide(data[os][datestr]["opt_test"],data[os][datestr]["opt_test_counter"]);
              value = Math.max(dbg_total,opt_total);
              
              //Convert from seconds to hours
              value = to_hours(value);
              
              //Form datapoint
              datapoint = [parseDate(datestr), value];
              
              //Push datapoint to the series
              series['data'].push(datapoint);
            }
            //Push each completed series to the overall dataset
            graph_data.push(series);
        }
        //Loading is complete!
        hide_loading();

        //Begin Line Chart
        var chart;
        jQuery(document).ready(function() {
            chart = new Highcharts.Chart({
                chart: {
                    renderTo: 'container',
                    type: 'spline'
                },
                title: {
                    text: 'Go Faster! - '+graph_title
                },
                subtitle: {
                    text: ''
                },
                xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: { // don't display the dummy year
                        month: '%b %e',
                        year: '%Y'
                    }
                },
                yAxis: {
                    title: {
                        text: 'Average Wait Time (Hours)'
                    },
                    min: 0
                },
                tooltip: {
                    formatter: function() {
                            return '<b>'+ this.series.name +'</b><br/>'+
                            Highcharts.dateFormat('%b %e, %Y', this.x) +': '+ this.y +' hours';
                    }
                },
                series: graph_data
            });
        });
        //End Line Chart
    }); //End $.getJSON
}

function show_overhead(params_type){
    //Setup and Teardown Averages Dashboard
    show_loading(); //Show loading div to keep user happy

    //Request data from api/turnaround and do stuff
    if(params_type){
        resourceURL = 'api/overhead?type='+params_type;
        graph_title = "Average setup/teardown times for "+params_type;
    }else{
        resourceURL = 'api/overhead';
        graph_title = "Combined average setup/teardown times for test and build";
    }
    $.getJSON(resourceURL, function(data) {
        $('#container').show();
        graph_data = [];

        //Group data by OS
        for (os in data){
            //Save each series into a set for display on the chart
            series = {};
            series.name = os;
            series.data = []
            for(datestr in data[os]){
                //Calculate datapoint display value
                dbg_total = divide(data[os][datestr]["debug_build"],data[os][datestr]["debug_build_counter"]) + divide(data[os][datestr]["debug_test"],data[os][datestr]["debug_test_counter"]);
                opt_total = divide(data[os][datestr]["opt_build"],data[os][datestr]["opt_build_counter"]) + divide(data[os][datestr]["opt_test"],data[os][datestr]["opt_test_counter"]);
                value = Math.max(dbg_total,opt_total);

                //Convert from seconds to hours
                value = to_hours(value);
              
                //Form datapoint
                datapoint = [parseDate(datestr), value];
              
                //Push datapoint to the series
                series['data'].push(datapoint);
            }
            //Push each completed series to the overall dataset
            graph_data.push(series);
        }
        //Loading is complete!
        hide_loading();

        //Begin Line Chart
        var chart;
        jQuery(document).ready(function() {
            chart = new Highcharts.Chart({
                chart: {
                    renderTo: 'container',
                    type: 'spline'
                },
                title: {
                    text: 'Go Faster! - '+graph_title
                },
                subtitle: {
                    text: ''
                },
                xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: { // don't display the dummy year
                        month: '%b %e',
                        year: '%Y'
                    }
                },
                yAxis: {
                    title: {
                        text: 'Average Setup+Teardown Time (Hours)'
                    },
                    min: 0
                },
                tooltip: {
                    formatter: function() {
                            return '<b>'+ this.series.name +'</b><br/>'+
                            Highcharts.dateFormat('%b %e, %Y', this.x) +': '+ this.y +' hours';
                    }
                },
                series: graph_data
            });
        });
        //End Line Chart
    }); //End $.getJSON
}

function show_mochitests(params_os, params_buildtype){
    //Slow Mochitests Dashboard
    show_loading(); //Show loading div to keep user happy

    $.getJSON('api/mochitest', function(data) {

        topSlowest = [];
        graph_data = [];
        for (x in data){
            for(y in data[x]["tests"]){
                //y is the name of the test
                //data[x]["tests"][y] is the value
                //$('#result').append(y);
                testRunTime=parseInt(data[x]["tests"][y], 10);
                topSlowest.push([testRunTime,y]);
                testRunTime = testRunTime.toString();
            }
        }

        //Write results out to div
        $('#result').append("<h1>Top 10 Slowest MochiTests</h1>");

        //Sort and print the top 10
        topSlowest.sort(sortPairs);
        topSlowest = rmDupPairs(topSlowest);

        //Generate zebra-striped list, also create defaults for the series array
        $('#result').append("<ol>");
        series = []
        for(i=1;i<11;i++){
            $('#result ol').append("<li>" + topSlowest[i][1] + " (" + topSlowest[i][0]+"ms)</li>");
            series[i] = {}
            series[i].name = basename(topSlowest[i][1]);
            series[i].data = []
        }
        $('#result').append("</ol>");


        //Calculate Dates for second data query
        var myDate = new Date();
        myDate.setDate(myDate.getDate()-14);
        startdate = ISODateString(myDate);//calculate a week ago
        enddate = ISODateString(new Date());//calculate today

        //Tack on extra params if supplied
        resourceURL = 'api/mochitest?startdate='+startdate+'&enddate='+enddate;
        if(params_buildtype){
            resourceURL += "&buildtype=" + params_buildtype;
        }
        if(params_os){
            resourceURL += "&os=" + params_os;
        }

        //This time get a timespan worth of data
        $.getJSON(resourceURL, function(moredata) {

            //Calculate Data Points
            for (x in moredata){
                for(j=1;j<11;j++){
                    var value;
                    try{
                        //Ensure that the speed of the test is a valid number
                        value = moredata[x]["tests"][topSlowest[j][1]];
                        if (value==undefined){
                            continue; //Skip undefined values in data traversal
                        }
                    }catch(err){
                        //Should not happen but continue if it does
                        continue;
                    }

                    datapoint = [parseDate(moredata[x]["date"]), value];

                    /*
                        Insert datapoint into list if it's a unique date,
                        otherwise replace value with the max execution time.
                        This ensures that our graph displays the slowest
                        runtime of each point.
                    */
                    if(series[j].data[0]==undefined){
                        series[j].data.push(datapoint);
                    }else{
                        var exists = 0;
                        for(k in series[j].data){
                            if(series[j].data[k][0]==datapoint[0]){ //If new point's date is the same as someone else
                                series[j].data[k][1] = Math.max(datapoint[1],series[j].data[k][1]);
                                exists = 1;
                            }
                        }
                        if(exists==0){
                            series[j].data.push(datapoint);
                        }
                    }
                }
            }

            //Push each series onto the graph as a separate line
            //10 series, one for each top-ten slowest tests.
            for(i=1;i<11;i++){
                graph_data.push(series[i]);
            }

            hide_loading(); //Hide loading screen on successful fetch
            //Begin Line Chart
            var chart;
            jQuery(document).ready(function() {
                chart = new Highcharts.Chart({
                    chart: {
                        renderTo: 'container',
                        type: 'spline'
                    },
                    title: {
                        text: 'Go Faster! - Slowest Mochitests'
                    },
                    subtitle: {
                        text: ''
                    },
                    xAxis: {
                        type: 'datetime',
                        dateTimeLabelFormats: { // don't display the dummy year
                            month: '%b %e',
                            year: '%Y'
                        }
                    },
                    yAxis: {
                        title: {
                            text: 'mochitest runtime (ms)'
                        },
                        min: 0
                    },
                    tooltip: {
                        formatter: function() {
                                return '<b>'+ this.series.name +'</b><br/>'+
                                Highcharts.dateFormat('%b %e, %Y', this.x) +': '+ this.y +' ms';
                        }
                    },
                    series: graph_data
                });
            });//End Line Chart
        }); //End .getJSON

    }); //End $.getJSON()
} //End show_mochitests


function show_buildcharts() {
  show_loading();
  $.getJSON("api/builds/", function(data) {
    hide_loading();
    
    var all_summaries = data['builds'];

    // reformat time/revision to look decent in summary form +
    // format the last job type
    all_summaries.forEach(function(buildday) {     
      buildday["builds"] = buildday["builds"].map(function(b) { 
        // get description of last job (FIXME: duplication with buildchart.js)
        var jobtype = b.last_event.jobtype;
        if (b.last_event.jobtype !== "talos") {
          jobtype = b.last_event.buildtype + " " + b.last_event.jobtype;
        }

        return { 'revision': b['revision'].slice(0,8),
                 'uid': b['uid'],
                 'time_taken': ((b['time_taken'])/60.0/60.0).toFixed(3),
                 'last_event': b.last_event.os + " " + jobtype
               };
      });
    });

    $('#result').replaceWith(ich.buildlist({ summaries: all_summaries }));
  });
}
           
function show_isthisbuildfaster() {
  show_loading();
  $.getJSON("api/itbf/jobs/", function(data) {

    hide_loading();

    $('#result').replaceWith(ich.itbf_form({ num_itbf_jobs: data['num_pending_jobs'] }));
    $("form#itbf_form").submit(function() {   
      $.ajax({
        type: 'POST',
        url: "api/itbf/jobs/",
        data: { 'tree': $('#tree').val(),
                'revision': $('#revision').val(),
                'submitter_email': $('#submitter_email').val(),
                'return_email': $('#return_email').val()
              },
        success: function(data) {
          $('#result').replaceWith(ich.itbf_submitted({ num_itbf_jobs: data['num_pending_jobs'] }));
        },
        error: function(obj, textStatus, errorThrown) {
          $('#result').replaceWith(ich.itbf_error());
        },
        dataType: 'json'
      });
      
      return false;
    });
  });

}

$(function() {
  $('#result').replaceWith(ich.index());
  var router = Router({
    '': {
      on: function() {
        $('#result').replaceWith(ich.index());
        $('#errors').html("");
        $('#container').html("");
      }
    },
    '/turnaround': {
      '/:type': {
        on: show_turnaround
      }
    },
    '/endtoend/': {
      on: show_endtoend
    },

    '/executiontime': {
      '/:type': {
        on: show_executiontime
      }
    },
    '/waittime': {
      '/:type': {
        on: show_waittime 
      }
    },
    '/overhead': {
      '/:type': {
        on: show_overhead 
      }
    },
    '/buildcharts': {
      on: show_buildcharts
    },
    '/isthisbuildfaster': {
      on: show_isthisbuildfaster
    }
  }).init();
});
