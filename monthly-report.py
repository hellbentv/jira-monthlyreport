#!/usr/bin/env python
# Copyright (C) 2014 Linaro
#
# Author: Alan Bennett <alan.bennett@linaro.org>
#
# This file, monthly-report.py, is a hack, it's not supported
#
# is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cards.py.  If not, see <http://www.gnu.org/licenses/>.
#


import ConfigParser
import argparse
import logging
import sys
import datetime
import codecs
import locale
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

from jira.client import JIRA
DEFAULT_LOGGER_NAME = "test.log"
logger = None
__version__ = "2014.01.1"
DEFAULT_LOGGER_NAME = "cards.dbg.log"


def connect_jira(logger):
    """Connect to Jira Instance

    """
    Config = ConfigParser.ConfigParser()
    Config.read("settings.cfg")
    jira_server = Config.get('Jira', 'Server')
    jira_user = Config.get('Jira', 'Username')
    jira_pass = Config.get('Jira', 'Password')

    try:
        logger.info("Connection to JIRA %s" % jira_server)
        jira = JIRA(options={'server': jira_server}, basic_auth=(jira_user, jira_pass))
        return jira
    except:
        logger.error("Failed to connect to JIRA")
        return None


def get_logger(name=DEFAULT_LOGGER_NAME, debug=False):
    """
    Retrieves a named logger. Default name is set in the variable
    DEFAULT_LOG_NAME. Debug is set to False by default.

    :param name: The name of the logger.
    :param debug: If debug level should be turned on
    :return: A logger instance.
    """
    logger = logging.getLogger(name)
    ch = logging.StreamHandler()

    if debug:
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        ch.setFormatter(formatter)
        logger.setLevel(logging.INFO)

    logger.addHandler(ch)
    return logger


def setup_args_parser():
    """Setup the argument parsing.

    :return The parsed arguments.
    """
    description = "Walk through the Cards and generate some metrics"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-t", "--team", required=True, help="Team / Jira Project")
    return parser.parse_args()


def get_carddetails(jira, db, issues):
    """get_worklog - Build an intermediate database of recently worked on issues

    :param jira: a database session
    :param db: Dictionary of components
    :param issues: A jira query result

    :return The parsed arguments.
    """
    logger.info(' Number of issues found [' + str(issues.__len__()) + ']')
    for issue in issues:
        logger.debug(issue.key + ' [' + issue.fields.summary + ']')

        if issue.fields.assignee is None:
            issueowner = "Unassigned"
        else:
            issueowner = issue.fields.assignee.name
        db.append({'key': issue.key,
                   'assignee': issueowner,
                   'summary': issue.fields.summary,
                   'fixversion': issue.fields.fixVersions[0].name if issue.fields.fixVersions.__len__() > 0 else "" ,
                   'confidence': issue.fields.customfield_11200,
                   'status': issue.fields.status.name,
                   'rank': issue.fields.customfield_10900,
                   'engineeringprogress': issue.fields.customfield_10204})


def stripspecial(incoming):
    if incoming is not None:
        return incoming.replace(u"\u2018", "'").replace(u"\u2019", "'")
    else:
        return ""


def linkit(incoming):
    return '<a href="http://cards.linaro.org/browse/' + incoming + '">' + incoming + '</a>'


def report(jira, db, issues, outfile):
    """report - Report by user the amount of time logged (percentage)
    """
    db_sorted = sorted(db, key=lambda field: field['rank'])
    old_assignee = ""
    old_parent = ""
    print >>outfile, '<table border=0>'
    for issue in db_sorted:
        print >>outfile, '<tr><td>&nbsp;&nbsp;</td><td><b>' + linkit(issue['key']) + ' - ' + issue['summary'] + '</b><br>'
        print >>outfile, 'Status: ' + issue['status']
        print >>outfile, ', Target Delivery: ' + issue['fixversion']
        if issue['confidence'] is None:
            print >> outfile, ', Confidence: ' + 'Not set'
        else:
            print >>outfile, ', Confidence: ' + issue['confidence'] + '<br>'
        print >>outfile, '<font size=-2>&nbsp;<br></font>'
        print >>outfile, '' + stripspecial(issue['engineeringprogress']) + '</td></tr>'
    print >>outfile, '</table>'


def walkcards():
    Config = ConfigParser.ConfigParser()
    Config.read("settings.cfg")

    args = setup_args_parser()

    global logger
    logger = get_logger(debug=args.debug)

    jira = connect_jira(logger)

    if jira is None:
        sys.exit(1)

    #default jira project= LSK
    team = 'LSK'
    if args.team is not None:
        team = args.team

    #Initialize dictionaries that will be used to store cards
    db = []
    basequery = ' project = card AND summary !~ epic AND component = ' + team
    basequery += ' AND updatedDate > -25d '
    #basequery += ' AND status not in (Closed)'
    basequery += ' AND level not in ("Private - reporter only")'
    basequery += ' ORDER BY rank'
    debugquery = ""

    queryrange = 25
    logger.debug('[' + str(queryrange) + ' results at a time]')
    logger.debug('[' + basequery + ']')
    if debugquery:
        logger.info('WARNING DEBUG ON [' + debugquery + ']')
    for i in range(0, queryrange):
        low = i * queryrange
        numResults = queryrange
        logger.debug('..')
        logger.debug(' ###  low:' + str(low) + '    high:' + str(queryrange - 1))
        issues = jira.search_issues(basequery + debugquery, startAt=low, maxResults=queryrange)
        if len(issues) <= 0:
            break

        get_carddetails(jira, db, issues)

    week = str(datetime.datetime.now().isocalendar()[1])
    year = str(datetime.datetime.now().isocalendar()[0])
    filename = 'MonthlyReport-' + team + '_week-' + year + '_' + week + '.html'
    logger.info('Report saved in [' + filename + ']')

    outfile = open(filename, 'w')
    report(jira, db, issues, outfile)
    outfile.close()


if __name__ == '__main__':
    sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    walkcards()
