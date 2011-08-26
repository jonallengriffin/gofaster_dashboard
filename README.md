# About

This is the source to the Mozilla Firefox GoFaster dashboard, which aims
to provide useful metrics and tools to help us reduce build and testing times
for Mozilla Firefox. It is part of GoFaster (also known as "BuildFaster")
project. For more information see: 

https://wiki.mozilla.org/ReleaseEngineering/BuildFaster

# How to configure

At the moment, this is a two step process. First, run the bootstrap.sh script
from the root directory of this project:

    ./bootstrap.sh

Then, copy over the sitewide cfg file with the sample one (you can modify the
settings if you want, though the defaults should be fine for getting something
up and running)

    cd src/dashboard/server && cp settings.cfg.example settings.cfg && cd ../../../

To run the server in test mode, do the following:

    cd src/dashboard/server && ../../../bin/python server.py

<FIXME: Describe how to deploy server>

# Credits / Acknowledgements

* HTML templating done using the ICanHaz library (http://icanhazjs.com/)
* Routing done using the SugarSkull library (http://hij1nx.github.com/SugarSkull)
* Pretty graphs generated with flot.js (http://code.google.com/p/flot/)
