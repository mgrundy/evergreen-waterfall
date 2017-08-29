#!/usr/bin/env python
"""
Copyright 2016 MongoDB, Inc.

Waterfall prints Evergreen waterfall data from the command line
"""

import colorama
import json
import optparse
import os.path
import re
import requests
import sys
import yaml

API_SERVER_DEFAULT = "https://evergreen.mongodb.com"

def parse_command_line():
    parser = optparse.OptionParser(usage="Usage: %prog [options]")

    parser.add_option("-a", dest="all_variants", action="store_true",
                      help="Show all build variants")
    parser.add_option("-d", dest="details", action="store_true",
                      help="Show failed tests")
    parser.add_option("-l", dest="links", action="store_true",
                      help="Show log links")
    parser.add_option("-n", dest="count", type="int",
                      help="How many revisions to review")
    parser.add_option("-p", dest="project",
                      help="Project name, default is from evergreen.yml")
    parser.add_option("-r", dest="regex", type="int",
                      help="Build variant regex. Overriden by -a")
    parser.add_option("-s", dest="summary", action="store_true",
                      help="Summarize all variants for the commit")

    parser.set_defaults(all_variants=False,
                        commit=None,
                        count=3,
                        details=False,
                        links=False,
                        project=None,
                        regex=None,
                        summary=False)

    return parser.parse_args()


def read_evg_config():
    # Expand out evergreen config file possibilities
    file_list = [
        "./.evergreen.yml",
        os.path.expanduser("~/.evergreen.yml"),
        os.path.expanduser("~/cli_bin/.evergreen.yml")]

    for filename in file_list:
        if os.path.isfile(filename):
            with open(filename, "r") as fstream:
                return yaml.load(fstream)
    return None

def build_waterfall(evg_cfg, options, api_server):
    """ Collect and display evergreen waterfall data """
    version_data = {"versions": []}
    rest_prefix = "/rest/v1/"
    project = None
    api_prefix = api_server + rest_prefix

    if options.project:
        project = options.project
    else:
        try:
            for proj_cfg in evg_cfg["projects"]:
                if proj_cfg["default"] == True:
                    project = proj_cfg["name"]
                    break
        finally:
            if not project:
                print "Need to have a default project in .evergreen.yml or use -p 'project name'"
                sys.exit(1)

    session = requests.Session()
    if evg_cfg and evg_cfg["user"] and evg_cfg["api_key"]:
        session.headers.update({"Auth-Username": evg_cfg["user"], "Api-Key": evg_cfg["api_key"]})

    print "Gathering data for project:", project
    # print (api_prefix + "projects/" + project + "/versions/")
    version_data = session.get(api_prefix + "projects/" + project + "/versions/").json()
    # print json.dumps(version_data, sort_keys=True,
    #                 indent=4, separators=(',', ': '))

    if options.count == 0 or options.count > len(version_data["versions"]):
        options.count = len(version_data["versions"])

    for i in range(options.count):
        build_status = {"success":0, "failed":0, "undispatched":0, "dispatched":0, "started":0}
        version = version_data["versions"][i]
        key, build = version["builds"].iteritems().next()
        build_date = get_date_from_build_id(build["build_id"])
        print_commit_header(version, build_date)

        # This gets moved to its own function?
        for key, build in version["builds"].iteritems():
            status_wrap = {"success":0, "failed":0, "undispatched":0, "dispatched":0, "started":0}
            failed_tasks = []
            for task_name, task in build["tasks"].iteritems():
                status_wrap[task["status"]] += 1
                if task["status"] == "failed":
                    failed_tasks.append({"name": task_name, "id": task["task_id"]})

            #if status_wrap["success"] or status_wrap["failed"] or status_wrap["started"]:
            if options.all_variants or not options.summary and status_wrap["failed"]:
                print variant(build["name"])
                print_status(status_wrap)
                #print "Failed Tasks", failed_tasks
                if options.details:
                    task_details(session, failed_tasks, api_prefix, evg_cfg["ui_server_host"], options.links)

            # Add the variant stats to the build summary stats.
            build_status["success"] += status_wrap["success"]
            build_status["failed"] += status_wrap["failed"]
            build_status["dispatched"] += status_wrap["dispatched"]
            build_status["undispatched"] += status_wrap["undispatched"]

        if options.summary:
            print_status(build_status)

def get_date_from_build_id(build_id):
   d = build_id[-17:].split("_")
   return "%s-%s-%s %s:%s:%s" % (d[1], d[2], d[0], d[3], d[4], d[5])


def print_status(build_status):
    "Print the waterfall boxes. Should we make format helper funcs?"

    # {"success":0, "failed":0, "undispatched":0, "dispatched":0, "started":0}
    print colorama.Back.GREEN + colorama.Fore.WHITE + colorama.Style.BRIGHT,
    print "  %d  " % build_status["success"],
    print colorama.Back.RED + colorama.Fore.WHITE + colorama.Style.BRIGHT,
    print "  %d  " % build_status["failed"],
    print colorama.Back.YELLOW + colorama.Fore.BLACK,
    print "  %d  " % build_status["dispatched"],
    print colorama.Back.WHITE + colorama.Fore.BLACK,
    print "  %d  " % build_status["undispatched"],
    print colorama.Style.RESET_ALL

def print_commit_header(version, build_date):
    print "\n\n",
    print colorama.Fore.WHITE + colorama.Style.BRIGHT + version["author"],
    #print colorama.Style.RESET_ALL, version["revision"][:5],
    print colorama.Fore.BLUE + colorama.Style.BRIGHT, version["message"].splitlines()[0], colorama.Style.RESET_ALL
    print build_date_str(build_date), version["revision"]

# Put in color formatting functions, failed() sys_error()
def build_date_str(string):
    return colorama.Fore.YELLOW + colorama.Style.BRIGHT + string + colorama.Style.RESET_ALL

def variant(string):
    return "\n" + colorama.Fore.YELLOW + string + colorama.Style.RESET_ALL

def failed(string):
    return colorama.Fore.RED + string + colorama.Style.RESET_ALL

def sys_error(string):
    return colorama.Fore.MAGENTA + string + colorama.Style.RESET_ALL

def task_details(session, failed_tasks, api_prefix, ui_server, links):

    for task in failed_tasks:
        task_status = session.get(api_prefix + "tasks/" + task["id"]).json()
        #print json.dumps(task_status, sort_keys=True,
        #                 indent=4, separators=(',', ': '))

        # Hopefully this picks up executions properly.
        if task_status["status_details"]["timed_out"]:
            print failed(task_status["display_name"]), "timed out."
            if links:
                print "Task Logs:", ui_server + "/task_log_raw/" + \
                      task_status["id"] + "/%d?type=T&text=true" % task_status["execution"]
        elif not task_status["test_results"]:
            print sys_error(task_status["display_name"]), "system error."
            if links:
                print "Task Logs:", ui_server + "/task_log_raw/" + \
                      task_status["id"] + "/%d?type=T&text=true" % task_status["execution"]
        else:
            for testname, test in task_status["test_results"].iteritems():
                if test["status"] == "fail":
                    print failed(testname), "failed."
                    if links:
                        print "Test log:", test["logs"]["url"]


    return None

def main():
    options, args = parse_command_line()

    colorama.init()

    evg_cfg = read_evg_config()

    try:
        api_server = evg_cfg["api_server_host"]
        # Makes some assumptions, but saves doing a full url parse.
        if api_server.endsWith("/api"):
            api_server = api_server[:-4]
    except:
        api_server = API_SERVER_DEFAULT

    build_waterfall(evg_cfg, options, api_server)

if __name__ == "__main__":
    main()
