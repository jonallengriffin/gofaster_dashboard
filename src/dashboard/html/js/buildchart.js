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
      return x.start_time; 
    }).reduce(function(x,y) { 
      return Math.min(x,y);
    });

    var max_time = events.map(function(x) { 
      return x.finish_time; 
    }).reduce(function(x,y) { 
      return Math.max(x,y);
    });

    $('#header').prepend(ich.buildchart_header({ build_id: summary['uid'], 
                                                 revision: summary['revision'], 
                                                 date: summary['submitted_at'],
                                                 totaltime: ((summary['time_taken_overall'])/60.0/60.0).toFixed(3) }));

    $('#buildchart').width(((max_time-min_time)/60.0)*4)+100; // 4 pixels/minute (+ some extra space for text)
    $('#buildchart').height(events.length*25); // 25 pixels per event
    
    function get_relative_time(t) {
      return (t-min_time)/60.0/60.0;
    }
    

    var i=events.length;
    var series = [];
    var elements = [];
    events.forEach(function(event) {
      // get job description
      var jobtype = event.jobtype;
      if (event.jobtype !== "talos") {
        jobtype = [ event.buildtype, event.jobtype ].join(" ");
      }
      if (event.suitename) {
        jobtype += " (" + event.suitename + ")";
      }
      var desc = event.os + " " + jobtype + " " + ((event.finish_time - event.start_time)/60.0).toFixed(3) + " min";
      series[series.length] = [get_relative_time(event.start_time), i, get_relative_time(event.finish_time), desc];
      i--;
    });
    var options = { series: { gantt: { active: true, show: true, barheight: 0.2 } }
		    ,xaxis:  { min: 0, max: get_relative_time(max_time)+1, axisLabel: 'Time (hours)' }
		    ,yaxis:  { min: 0, max: series.length + 0.5, ticks: 0 }
		    ,grid:   { hoverable: true, clickable: true}
   		  };
    $.plot($("#buildchart"), [ { data: series } ], options);
  });
});