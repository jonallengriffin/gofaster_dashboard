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
 * Portions created by the Initial Developer are Copyright (C) 2011
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

function show_endtoend(mode) {
  show_loading(); //Show loading div to keep user happy

  $.getJSON('api/endtoendtimes?mode=' + mode, function(data) {
    hide_loading();
    $('#container').show();
;    
    var end_to_end_times = data.end_to_end_times;
    
    var graphdata;
    if (mode === "os") {
      $('#result').append("<h3>Go Faster! - Average End to End Performance per OS</h3><br/>");
      graphdata = Object.keys(end_to_end_times).map(function(os) {
        var series = {};
        series.label = os;
        series.data = end_to_end_times[os].map(function(datapoint) {
          return [parseDate(datapoint[0]), to_hours(datapoint[1])];
        });
        return series;
      });
    } else {
      $('#result').append("<h3>Go Faster! - Average End to End Performance</h3><br/>");
      var series = {};
      series.data = end_to_end_times.map(function(datapoint) {
        return [parseDate(datapoint[0]), to_hours(datapoint[1])];
      });

      graphdata = [ series ];
    }
    
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
  
  if (params_type) {
    resourceURL = 'api/executiontime?type='+params_type;
    graph_title = "Average execution times for "+params_type;
  } else {
    resourceURL = 'api/waittime';
    graph_title = "Combined average execution times for build and test";
  }
  
  $.getJSON(resourceURL, function(data) {
    hide_loading();
    $('#container').show();
    
    var graphdata = Object.keys(data).map(function(os) {
      var series = {};
      series.label = os;
      series.data = Object.keys(data[os]).map(function(datestr) {      
        var dbg_total = divide(data[os][datestr]["debug_build"],
                               data[os][datestr]["debug_build_counter"]) + 
          divide(data[os][datestr]["debug_test"],
                 data[os][datestr]["debug_test_counter"]);
        var opt_total = divide(data[os][datestr]["opt_build"],
                               data[os][datestr]["opt_build_counter"]) + 
          divide(data[os][datestr]["opt_test"],
                 data[os][datestr]["opt_test_counter"]);
        
        return [parseDate(datestr), to_hours(Math.max(dbg_total,opt_total))];
      }).sort(function(a,b) { return a[0]-b[0]; });

      return series;
    });

    hide_loading();

    $('#result').append("<h3>Go Faster! - " + graph_title + "</h3><br/>");

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

      var graphdata = Object.keys(data).map(function(os) {
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

          return [parseDate(datestr), to_hours(Math.max(dbg_total,opt_total))];
        }).sort(function(a,b) { return a[0]-b[0]; });
        
        return series;
      });

      hide_loading();

      $('#result').append("<h3>Go Faster! - " + graph_title + "</h3><br/>");
      
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

      var graphdata = Object.keys(data).map(function(os) {
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

          return [parseDate(datestr), to_hours(Math.max(dbg_total,opt_total))];
        }).sort(function(a,b) { return a[0]-b[0]; });
        
        return series;
      });

      hide_loading();
      $('#result').append("<h3>Go Faster! - " + graph_title + "</h3><br/>");
      
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
    '/endtoend': {
      '/:mode': {
        on: show_endtoend
      }
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
