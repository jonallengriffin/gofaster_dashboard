#!/usr/bin/python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Mozilla War on Orange Mailer.
#
# The Initial Developer of the Original Code is
# Mozilla foundation
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Mark Cote <mcote@mozilla.com>
#   William Lachance <wlachance@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

# Script to process buildfaster jobs
# (much of this gratuitously copied from: http://hg.mozilla.org/automation/orangefactor/file/5894e67315f8/woo_mailer.py)

import pickle
import isthisbuildfaster
import tempita
import ConfigParser
from sendemail import SendEmail
import queue
import os

email_tmpl = '''We compared '{{revision}}' against the following revisions of mozilla-central:
{{for r in compare_revisions}}
{{r}}
{{endfor}}

Summary of results
------------------

Total test time for '{{revision}}': {{testtime}}
Mean total test time of last 10 revisions: {{last10_mean}}
Standard deviation of last 10 revisions: {{last10_stdev}}

Notable Results (> 2* faster/slower than standard deviation)
------------------------------------------------------------

{{notableresults}}

All Results
-----------

{{allresults}}

Visit the gofaster dashboard at {{exturl}}/

Brought to you by the Mozilla A-Team.

https://wiki.mozilla.org/Auto-tools
IRC channel #ateam
'''

DEFAULT_CONF_FILE = os.path.dirname(os.path.realpath(__file__)) + '/../settings.cfg'

def main():
    import errno, sys
    from optparse import OptionParser
    
    parser = OptionParser()
    parser.add_option('-c', '--config', action='store', type='string',
                      dest='config_file', default=DEFAULT_CONF_FILE, help='specify config file')
    parser.add_option('-t', '--test', action='store_true', dest='test_mode',
                      help='test mode, check options and print email to screen but do not send')
    (options, args) = parser.parse_args()
    
    cfg = ConfigParser.ConfigParser()
    cfg.read(options.config_file)

    try:
        local_server_url = cfg.get('gofaster', 'local_server_url')
        external_server_url = cfg.get('gofaster', 'external_server_url')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        sys.stderr.write('"local_server_url" and "external_server_url" options not found in\n"gofaster" section in file "%s".\n' % options.config_file)
        sys.exit(errno.EINVAL)

    try:
        mail_username = cfg.get('email', 'username')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        sys.stderr.write('No "username" option defined in "email" section of file "%s".' % options.config_file)
        sys.exit(errno.EINVAL)
    
    try:
        mail_password = cfg.get('email', 'password')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_password = None
        
    try:
        mail_server = cfg.get('email', 'server')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_server = 'mail.mozilla.com'
    
    try:
        mail_port = cfg.getint('email', 'port')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_port = 465
        
    try:
        mail_ssl = cfg.getboolean('email', 'ssl')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_ssl = True

    # Get the next job from the queue
    job = queue.pop_job()
    if not job:
        print "No pending jobs"
        exit(0)

    data = isthisbuildfaster.compare_test_durations('mozilla-central', None,
                                                    job['tree'], 
                                                    job['revision'], 
                                                    job['submitter'])
    #import json
    #data = json.loads(open('/home/wlach/src/gofaster/isthisbuildfaster2.json', 'r').read())

    revision = '%s %s' % (job['tree'], job['revision'])
    mozilla_central_revisions = data['revisions'][0]['revision']

    notable_results = []
    allresults_text = ""
    for (platform_name, platform) in data["durations"].iteritems():
        resultlines = []
        for (test_name, test) in sorted(platform.iteritems(), key=lambda t: t[0]):
            diff = test['mean'] - test['testtime']
            resultlines.append(", ".join(str(i) for i in ([test_name, test['mean'], test['testtime'], diff])))
            if abs(test['testtime']-test['mean']) > 2*test['stdev']:
                notable_results.append({ 'platform': platform_name, 
                                         'test': test_name, 
                                         'testtime': test['testtime'],
                                         'mean': test['mean'],
                                         'stdev': test['stdev'],
                                         'diff': diff })
                               
        allresults_text += "Results for %s\n" % platform_name
        allresults_text += "Suite, Mean result, %s, diff (seconds)\n" % revision
        allresults_text += "\n".join(resultlines)

    notable_text=""
    if len(notable_results) > 0:
        notable_text += "Platform, Suite, %s, Mean, stdev, diff (seconds)" % revision
        for notable_result in sorted(notable_results, key=lambda r: r['test'] + (r['platform']*10)):
            notable_text += '\n'
            notable_text += ', '.join( str(i) for i in [ notable_result['platform'], 
                                                         notable_result['test'], 
                                                         notable_result['testtime'], 
                                                         notable_result['mean'], 
                                                         notable_result['stdev'],
                                                         notable_result['diff'] ])
    else:
        notable_text = "No notable results"

    subject = 'Is this build faster? Results for %s' % revision
    tmpl = tempita.Template(email_tmpl)
    text = tmpl.substitute({'subject': subject,
                            'revision': revision,
                            'compare_revisions': mozilla_central_revisions,
                            'testtime': data['totals']['testtime'],
                            'last10_mean': data['totals']['mean'],
                            'last10_stdev': data['totals']['stdev'],                           
                            'exturl': external_server_url,
                            'notableresults': notable_text,
                            'allresults': allresults_text})
    to = [ job['return_email'] ]

    if options.test_mode:
        print 'From: %s' % mail_username
        print 'To: %s' % " ".join(to)
        print 'Subject: %s' % subject
        print
        print text
    else:
        print 'Sending email to %s...' % ', '.join(to)
        SendEmail(From=mail_username, To=to, Subject=subject,
                  Username=mail_username, Password=mail_password, TextData=text,
                  Server=mail_server, Port=mail_port, UseSsl=mail_ssl)
        print 'Done!'

if __name__ == '__main__':
    main()
