# About

This is the source to the Mozilla Firefox GoFaster dashboard, which aims
to provide useful metrics and tools to help us reduce build and testing times
for Mozilla Firefox.

# How to configure

At the moment, this is a two step process. First, run the bootstrap.sh script
from the root directory of this project:

    ./bootstrap.sh

Then, copy over the sitewide cfg file with the sample one (you can modify the
settings if you want, though the defaults should be fine for getting something
up and running)

    cd src/dashboard/server && cp settings.cfg.example settings.cfg && cd ../../../

# Credits / Acknowledgements

* HTML templating done using the ICanHaz library (http://icanhazjs.com/)
* Pretty graphs generated with HighCharts (http://www.highcharts.com/). Note 
that HighCharts is only free for non-commercial use. 
