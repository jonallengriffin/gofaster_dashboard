# About

This is the source to the Mozilla Firefox GoFaster dashboard, which aims
to provide useful metrics and tools to help us reduce build and testing times
for Mozilla Firefox. It is part of GoFaster (also known as "BuildFaster")
project. For more information see: 

https://wiki.mozilla.org/ReleaseEngineering/BuildFaster

# How to configure

At the moment, this is a three step process. First, run the bootstrap.sh script
from the root directory of this project:

    ./bootstrap.sh

You'll also need to process a copy of release engineering's build data for most of the
views to work:

    ./bin/fetch-and-process-builddata.sh

If desired, edit the server config file (the defaults should be fine for
getting something up and running though). It is located in
`src/dashboard/server/settings.cfg`.

To run the server in test mode, do the following from the root directory:

    ./bin/runserver.sh

<FIXME: Describe how to deploy server>

# Credits / Acknowledgements

* HTML templating done using the ICanHaz library (http://icanhazjs.com/)
* Routing done using the SugarSkull library (http://hij1nx.github.com/SugarSkull)
* Pretty graphs generated with flot.js (http://code.google.com/p/flot/)
