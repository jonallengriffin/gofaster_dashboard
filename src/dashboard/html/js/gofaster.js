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

function show_graph(data) {
  $('#container').html(null); // wipe out any previously generated graph
  $('#graphtooltip').remove(); // wipe out any still open tooltips

  $.plot($("#container"), data, {
    xaxis: {
      mode: "time"
    },
    yaxis: {
      axisLabel: 'Time (Hours)',
      min: 0
    },
    series: {
      lines: { show: true, fill: false, steps: false },
      points: { show: true }
    },
    legend: {
      position: "nw",
      hideable: true
    },
    grid: {
      hoverable: "true"
    }
  });

  $("#container").bind("plothover", function (event, position, item) {
    if(item) {
        var x = item.datapoint[0].toFixed(2),
            y = item.datapoint[1].toFixed(2);

        show_graph_tooltip(item.pageX, item.pageY, "Build time (hours): " + y);
    }
  });
}

function show_graph_tooltip(x, y, content) {

  $("#graphtooltip").remove();

  $('<div id="graphtooltip">' + content + '</div>')
    .css({top: y + 5,
          left: x + 5})
    .appendTo('body')
    .fadeIn(200);

}

function create_paramstr(paramdict) {
  return Object.keys(paramdict).map(function(key) {
    return key + "=" + paramdict[key];
  }).join("&");
}

function parse_paramstr(paramstr, defaultdict) {
  // create object, copy defaults
  var paramdict = {};
  Object.keys(defaultdict).forEach(function(key) {
    paramdict[key] = defaultdict[key];
  });

  // parse explicit parameters
  if (paramstr) {
    paramstr.slice(1).split("&").forEach(function(p) {
      var keyval = p.split("=");
      if (!isNaN(keyval[1])) {
        paramdict[keyval[0]] = +keyval[1];
      } else {
        paramdict[keyval[0]] = keyval[1];
      }
    });
  }

  return paramdict;
}

function update_form_options(endpoint, type, params) {
  $("#range" + params.range).attr("selected", "true");
  $("#range").change(function() {
    params.range = $(this).val();
    window.location.hash = '/' + [ endpoint, type ].join("/") + "?" + create_paramstr(params);
  });

  $("#include_outliers").prop("checked", !!params.include_outliers);
  $("#include_outliers").change(function() {
    params.include_outliers = +($(this).prop("checked"));
    window.location.hash = '/' + [ endpoint, type ].join("/") + "?" + create_paramstr(params);
  });
}

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

//Each function below represents a graph to be displayed (yes, there's a lot of duplication)

function show_endtoend(mode, params) {
  $('#rightcontent').html(ich.graph({
    title: mode === "os" ? "Average End to End Performance per OS" : "Average End to End Performance",
    comment: "Averages only include the first build for each revision (this excludes Nightly and PGO builds)"
  }));
  update_form_options('endtoend', mode, params);

  $.getJSON('api/endtoendtimes/' + mode +'?' + create_paramstr(params), function(data) {
    var graphdata = Object.keys(data).sort().map(function(os) {
      var series = {};
      if (mode === "per_os") {
        series.label = os;
      }
      series.data = Object.keys(data[os]).map(function(datestr) {
        return [parseDate(datestr), to_hours(data[os][datestr])];
      }).sort();

      return series;
    });

    show_graph(graphdata);
  });
}

//Build and Test Execution Dashboard
function show_executiontime(type, params) {
  $('#rightcontent').html(ich.graph({
    title: "Average execution times for "+type,
    comment: null
  }));
  update_form_options('executiontime', type, params);

  $.getJSON('api/executiontime/'+type+'?' + create_paramstr(params), function(data) {
    var graphdata = Object.keys(data).sort().map(function(os) {
      var series = {};
      series.label = os;
      series.data = Object.keys(data[os]).map(function(datestr) {
        return [parseDate(datestr), to_hours(data[os][datestr])];
      }).sort();

      return series;
    });

    show_graph(graphdata);
  });
}

function show_waittime(type, params) {
  $('#rightcontent').html(ich.graph({
    title: "Average wait times for " + type,
    comment: null
  }));
  update_form_options('waittime', type, params);

  $.getJSON('api/waittime/'+ type + '?' + create_paramstr(params), function(data) {
    var graphdata = Object.keys(data).sort().map(function(os) {
      var series = {};
      series.label = os;
      series.data = Object.keys(data[os]).map(function(datestr) {
        return [parseDate(datestr), to_hours(data[os][datestr])];
      }).sort();

      return series;
    });

    show_graph(graphdata);
  });
}

function show_overhead(type, params) {
  $('#rightcontent').html(ich.graph({
    title: "Average setup/teardown times for " + type,
    comment: null
  }));
  update_form_options('overhead', type, params);

  $.getJSON('api/overhead/'+ type + '?' + create_paramstr(params), function(data) {
    var graphdata = Object.keys(data).sort().map(function(os) {
      var series = {};
      series.label = os;
      series.data = Object.keys(data[os]).map(function(datestr) {
        return [parseDate(datestr), to_hours(data[os][datestr])];
      }).sort();

      return series;
    });

    show_graph(graphdata);
  });
}

function show_buildcharts() {
  $('#rightcontent').html(ich.dialog({ title:"Build charts" }));

  $.getJSON("api/builds/", function(data) {
    var all_summaries = data;
    $('#dialog_content').html(ich.buildcharts({ summaries: all_summaries }));
  });
}

function show_isthisbuildfaster() {

  $('#rightcontent').html(ich.dialog({ title:"Is this build faster?" }));

  $.getJSON("api/itbf/jobs/", function(data) {
    $('#dialog_content').html(ich.itbf_form({ num_itbf_jobs: data['num_pending_jobs'] }));
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
          $('#dialog_content').replaceWith(ich.itbf_submitted({ num_itbf_jobs: data['num_pending_jobs'] }));
        },
        error: function(obj, textStatus, errorThrown) {
          $('#dialog_content').replaceWith(ich.itbf_error());
        },
        dataType: 'json'
      });

      return false;
    });
  });

}

$(function() {
  var router = Router({
    '/': {
      on: function() {
        $('#rightcontent').html(ich.index());
      }
    },
    '/endtoend': {
      '/(average|per_os)(\\?(.*))?': {
        on: function(mode, paramstr) {
          var paramdict = parse_paramstr(paramstr, { range: 30, include_outliers: 0 });
          show_endtoend(mode, paramdict);
        }
      }
    },

    '/executiontime': {
      '/(build|test)(\\?(.*))?': {
        on: function(type, paramstr) {
          var paramdict = parse_paramstr(paramstr, { range: 30, include_outliers: 0 });
          show_executiontime(type, paramdict);
        }
      }
    },
    '/waittime': {
      '/(build|test)(\\?(.*))?': {
        on: function(type, paramstr) {
          var paramdict = parse_paramstr(paramstr, { range: 30, include_outliers: 0 });
          show_waittime(type, paramdict);
        }
      }
    },
    '/overhead': {
      '/(build|test)(\\?(.*))?': {
        on: function(type, paramstr) {
          var paramdict = parse_paramstr(paramstr, { range: 30, include_outliers: 0 });
          show_overhead(type, paramdict);
        }
      }
    },
    '/buildcharts': {
      on: show_buildcharts
    },
    '/isthisbuildfaster': {
      on: show_isthisbuildfaster
    }
  }).init('/');
});
