$(function() {
  // hackily get the buildid parameter
  // from: from: http://jquery-howto.blogspot.com/2009/09/get-url-parameters-values-with-jquery.html
  var vars = [], hash;
  var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
  for(var i = 0; i < hashes.length; i++)
  {
    hash = hashes[i].split('=');
    vars.push(hash[0]);
    vars[hash[0]] = hash[1];
  }  
  
  // get the data!
  $.getJSON('api/builddata/?buildid=' + vars['buildid'], function(data) {

    var events = data['events'];
    var summary = data['summary'];

    var min_time = events.map(function(x) { 
      return x.submitted_at; 
    }).reduce(function(x,y) { 
      return Math.min(x,y);
    });

    var max_time = events.map(function(x) { 
      return x.finish_time; 
    }).reduce(function(x,y) { 
      return Math.max(x,y);
    });

    var submitted_date = new Date(summary['submitted_at']*1000);

    $('#header').prepend(ich.buildchart_header({ build_id: summary['uid'], 
                                                 revision: summary['revision'], 
                                                 date: submitted_date.toUTCString(),
                                                 totaltime: ((summary['time_taken_overall'])/60.0/60.0).toFixed(3) }));

    $('#buildchart').width(((max_time-min_time)/60.0)*5); // 5 pixels/minute (+ some extra space for text)
    $('#buildchart').height(events.length*25); // 25 pixels per event
    
    function get_relative_time(t) {
      return (t-min_time)/60.0/60.0;
    }
    
    var i=events.length;
    var event_series = [];
    var submitted_series = [];
    events.forEach(function(event) {
      // get job description
      var jobtype = event.jobtype;
      if (event.jobtype !== "talos") {
        jobtype = [ event.buildtype, event.jobtype ].join(" ");
      }
      if (event.suitename) {
        jobtype += " (" + event.suitename + ")";
      }

      function toMinuteString(seconds) {
        return (seconds/60.0).toFixed(3) + " min";
      }

      var desc = event.os + " " + jobtype + " " + toMinuteString(event.finish_time - event.start_time) + " (wait: " + toMinuteString(event.start_time - event.submitted_at) + ")";
      event_series[event_series.length] = [get_relative_time(event.start_time), i, get_relative_time(event.finish_time), desc];
      submitted_series[submitted_series.length] = [get_relative_time(event.submitted_at), i, get_relative_time(event.start_time), null];
      console.log(event.start_time-event.submitted_at);
      i--;
    });
    var options = { series: { gantt: { active: true, show: true, barheight: 0.2 } }
		    ,xaxis:  { min: 0, max: get_relative_time(max_time)+1, axisLabel: 'Time (hours)' }
		    ,yaxis:  { min: 0, max: event_series.length + 0.5, ticks: 0 }
		    ,grid:   { hoverable: true, clickable: true}
   		  };
    $.plot($("#buildchart"), [ { label: "Events", data: event_series }, { label: "Wait times", data: submitted_series } ], options);
  });
});