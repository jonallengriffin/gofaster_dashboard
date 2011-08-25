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
                                                 totaltime: ((summary['time_taken'])/60.0/60.0).toFixed(3) }));


    var canvas = document.getElementById('canvas');
    canvas.width=((max_time-min_time)/60.0)*5 + 200; // 5 pixels/minute (+ some extra space for text)
    canvas.height=events.length*20; // 20 pixels per event

    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ddd";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    var y=0;
    events.forEach(function(entry) {
      var x1 = (entry.start_time - min_time)/60.0*5;
      var x2 = (entry.finish_time - min_time)/60.0*5;
      console.log("x1: " + x1 + " x2: " + x2);
      ctx.fillStyle = "#aaf";
      ctx.fillRect(x1, y, x2-x1, 20);

      var jobtype = entry.jobtype;
      if (entry.jobtype !== "talos") {
        jobtype = entry.buildtype + " " + entry.jobtype;
      }
      var time_taken_str = ((entry.finish_time - entry.start_time)/60.0).toFixed(3) + " minutes";
      
      ctx.fillStyle = "#000";
      ctx.textBaseline = "top";
      ctx.fillText(entry.os + " " + jobtype + " " + time_taken_str, x1, y+2);
      
      y+=20.0;
    });
  });
});