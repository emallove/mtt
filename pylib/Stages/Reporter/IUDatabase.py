# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: f; python-indent: 4 -*-
#
# Copyright (c) 2015-2016 Intel, Inc. All rights reserved.
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
#

import os
import pwd
import requests
import json
import pprint
import re
from datetime import datetime
from requests.auth import HTTPBasicAuth

from ReporterMTTStage import *

class IUDatabase(ReporterMTTStage):

    def __init__(self):
        # initialise parent class
        ReporterMTTStage.__init__(self)
        self.options = {}
        self.options['realm'] = (None, "Database name")
        self.options['username'] = (None, "Username to be used for submitting data")
        self.options['password'] = (None, "Password for that username")
        self.options['pwfile'] = (None, "File where password can be found")
        self.options['platform'] = (None, "Name of the platform (cluster) upon which the tests were run")
        self.options['hostname'] = (None, "Name of the hosts involved in the tests (may be regular expression)")
        self.options['url'] = (None, "URL of the database server")
        self.options['debug_filename'] = (None, "Debug output file for server interaction information")
        self.options['keep_debug_files'] = (False, "Retain reporter debug output after execution")
        self.options['debug_server'] = (False, "Ask the server to return its debug output as well")
        self.options['email'] = (None, "Email to which errors are to be sent")

    def activate(self):
        # get the automatic procedure from IPlugin
        IPlugin.activate(self)
        return


    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def print_name(self):
        return "IUDatabase"

    def print_options(self, testDef, prefix):
        lines = testDef.printOptions(self.options)
        for line in lines:
            print prefix + line
        return

    def execute(self, log, keyvals, testDef):
        # parse the provided keyvals against our options
        cmds = {}
        testDef.parseOptions(log, self.options, keyvals, cmds)

        # quick sanity check
        sanity = 0
        if cmds['username'] is not None:
            sanity += 1
        if cmds['password'] is not None or cmds['pwfile'] is not None:
            sanity += 1
        if cmds['realm'] is not None:
            sanity += 1
        if 0 < sanity and sanity != 3:
            log['status'] = 1
            log['stderr'] = "MTTDatabase Reporter section",log['section'] + ": if password, username, or realm is specified, they all must be specified."
            return
        try:
            if cmds['pwfile'] is not None:
                if os.path.exists(cmds['pwfile'][0]):
                    f = open(cmds['pwfile'][0], 'r')
                    password = f.readline().strip()
                    f.close()
                else:
                    log['status'] = 1;
                    log['stderr'] = "Password file " + cmds['pwfile'][0] + " does not exist"
                    return
            elif cmds['password'] is not None:
                password = cmds['password']
        except KeyError:
            try:
                if cmds['password'] is not None:
                    password = cmds['password'][0]
            except KeyError:
                pass
        #
        # Setup the JSON data structure
        #
        s = requests.Session()
        url = cmds['url'] + "/submit"
        if 0 < sanity:
            www_auth = HTTPBasicAuth(cmds['username'], password)
        else:
            www_auth = None

        # Get a client serial number
        client_serial = self._get_client_serial(s, cmds['url'], www_auth)
        if client_serial < 0:
            print "Error: Unable to get a client serial (rtn=%d)" % (client_serial)

        headers = {}
        headers['content-type'] = 'application/json'

        data = {}

        profile = testDef.logger.getLog('Profile:Installed')
        metadata = {}
        metadata['client_serial'] = client_serial
        metadata['hostname'] = profile['profile']['nodeName']
        metadata['http_username'] = cmds['username']
        metadata['local_username'] = pwd.getpwuid(os.getuid()).pw_name
        metadata['mtt_client_version'] = '4.0a1'
        metadata['platform_name'] = self._extract_param(testDef.logger, 'MTTDefaults', 'platform')
        metadata['trial'] = int(self._extract_param(testDef.logger, 'MTTDefaults', 'trial'))

        # Strategy:
        # For each Test Run section
        #  - Find 'parent' Test Build
        #    - Find 'middleware' MiddlewareBuild (MPI Install)
        #      - Submit MPI Install phase
        #    - Submit Test Build phase
        #  - for each test run result
        #    - Submit Test Run phase

        # get the entire log of results
        fullLog = testDef.logger.getLog(None)
        pp = pprint.PrettyPrinter(indent=4)

        #
        # Dump the entire log
        #
        print "<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>"
        for lg in fullLog:
            print "----------------- Section (%s) " % (lg['section'])
            pp.pprint(lg)
        print "<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>"

        #
        # Process the test run sections
        #
        for lg in fullLog:
            # Find sections prefixed with 'TestRun'
            if re.match("TestRun", lg['section']):
                rtn = self._submit_test_run(testDef.logger, lg, metadata, s, url, www_auth)

        log['status'] = 0
        return

    def _merge_dict(self, x, y):
        z = x.copy()
        z.update(y)
        return z

    def _submit_test_run(self, logger, lg, metadata, s, url, httpauth=None):
        print "----------------- Test Run (%s) " % (lg['section'])

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(lg)

        # Find 'parent' Test Build - submit
        test_info = self._submit_test_build(logger,
                                      logger.getLog(self._extract_param(logger, lg['section'], 'parent')),
                                      metadata,
                                      s, url, httpauth)
        if test_info is None:
            return None

        # get the options used to do the run
        try:
            options = lg['options']
        except KeyError:
            return None

        #
        # Prepare to submit
        # JJH Todo fill these fields in
        #
        metadata['phase'] = 'Test Run'

        common_data = {}
        #common_data['mpi_install_id'] = None
        # For now assume that we only had one test_build submitted
        # and all of the tests that follow are from that test_build
        common_data['test_build_id'] = test_info['ids'][0]['test_build_id']

        for trun in testresults:
            data = {}

            #data['mpi_install_id'] = common_data['mpi_install_id']
            data['test_build_id'] = common_data['test_build_id']

            try:
                data['launcher'] = options['command']
            except KeyError:
                data['launcher'] = None

            data['test_name'] = None

            try:
                data['np'] = options['np']
            except KeyError:
                data['np'] = None

            data['full_command'] = None

            # For now just mark the time when submitted
            data['start_timestamp'] = datetime.utcnow().strftime("%c")

            data['result_message'] = None
            data['test_result'] = None

            try:
                data['exit_value'] = lg['status']
            except KeyError:
                data['exit_value'] = None

            # Optional
            # data['duration'] = None

            # data['exit_signal'] = None

            # data['resource_manager'] = None
            # data['parameters'] = None
            # data['network'] = None

            # data['latency_bandwidth'] = None
            # data['message_size'] = None
            # data['latency_min'] = None
            # data['latency_avg'] = None
            # data['latency_max'] = None
            # data['bandwidth_min'] = None
            # data['bandwidth_avg'] = None
            # data['bandwidth_max'] = None

            # data['description'] = None
            # data['environment'] = None

            try:
                if options['merge_stdout_stderr']:
                    data['merge_stdout_stderr'] = 1
                else:
                    data['merge_stdout_stderr'] = 0
            except KeyError:
                data['merge_stdout_stderr'] = None

            try:
                data['result_stdout'] = lg['stdout']
            except KeyError:
                data['result_stdout'] = None

            try:
                data['result_stderr'] = lg['stderr']
            except KeyError:
                data['result_stderr'] = None

            #
            # Submit
            #
            payload = {}
            payload['metadata'] = metadata
            payload['data'] = [data]

            data = self._submit_json_data(payload, s, url, httpauth)
            if data is None:
                return None
            if data['status'] is not 0:
                return None

        return True

    def _submit_test_build(self, logger, lg, metadata, s, url, httpauth=None):
        print "----------------- Test Build (%s) " % (lg['section'])

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(lg)

        # Find 'parent' Test Get (not needed)
        # Find 'middleware' MiddlewareBuild (MPI Install)
        install_info = self._submit_install(logger,
                                   logger.getLog(self._extract_param(logger, lg['section'], 'middleware')),
                                   metadata,
                                   s, url, httpauth)
        if install_info is None:
            return None

        # get the options used to do the run
        try:
            options = lg['options']
        except KeyError:
            return None

        #
        # Prepare to submit
        # JJH Todo fill these fields in
        #
        data = {}
        metadata['phase'] = 'Test Build'

        # For now assume that we only had one mpi_install submitted
        data['mpi_install_id'] = install_info['ids'][0]['mpi_install_id']

        data['compiler_name'] = None
        data['compiler_version'] = None

        data['suite_name'] = None

        # For now just mark the time when submitted
        data['start_timestamp'] = datetime.utcnow().strftime("%c")

        data['result_message'] = None
        data['test_result'] = None
        data['exit_value'] = None

        # Optional
        #data['duration'] = None

        #data['exit_signal'] = None
        #data['description'] = None
        #data['environment'] = None

        try:
            if options['merge_stdout_stderr']:
                data['merge_stdout_stderr'] = 1
            else:
                data['merge_stdout_stderr'] = 0
        except KeyError:
            data['merge_stdout_stderr'] = None

        try:
            data['result_stdout'] = lg['stdout']
        except KeyError:
            data['result_stdout'] = None

        try:
            data['result_stderr'] = lg['stderr']
        except KeyError:
            data['result_stderr'] = None


        #
        # Submit
        #
        payload = {}
        payload['metadata'] = metadata
        payload['data'] = [data]

        data = self._submit_json_data(payload, s, url, httpauth)
        if data is None:
            return None
        if data['status'] is not 0:
            return None

        # Extract ID
        return self._merge_dict( {'test_build_id':data['ids']['test_build_id']},
                                 install_info)

    def _submit_install(self, logger, lg, metadata, s, url, httpauth=None):
        print "----------------- MPI Install (%s) " % (lg['section'])
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(lg)

        # Find 'parent' MiddlewareGet (MPI Get) (not needed?)

        # get the options used to do the run
        # no options for MPI Install (?)
        # try:
        #     options = lg['options']
        # except KeyError:
        #     print "Error: Failed to get 'options'"
        #     return None
        options = None

        # get the system profile
        profile = logger.getLog('Profile:Installed')['profile']
        if profile is None:
            print "Error: Failed to get 'profile'"
            return None

        #
        # Prepare to submit
        # JJH Todo fill these fields in
        #
        data = {}
        metadata['phase'] = 'MPI Install'

        try:
            data['platform_hardware'] = profile['machineName']
        except KeyError:
            data['platform_hardware'] = None

        try:
            data['platform_type'] = profile['processorType']
        except KeyError:
            data['platform_type'] = None

        try:
            data['os_name'] = profile['kernelName']
        except KeyError:
            data['os_name'] = None

        try:
            data['os_version'] = profile['kernelRelease']
        except KeyError:
            data['os_version'] = None

        data['compiler_name'] = None
        data['compiler_version'] = None

        data['mpi_name'] = None
        data['mpi_version'] = None

        data['configure_arguments'] = None

        # For now just mark the time when submitted
        data['start_timestamp'] = datetime.utcnow().strftime("%c")

        data['result_message'] = None
        data['test_result'] = None
        data['exit_value'] = None

        # Optional
        # data['duration'] = None

        # data['vpath_mode'] = None
        # data['bitness'] = None
        # data['endian'] = None

        #data['exit_signal'] = None
        #data['description'] = None
        #data['environment'] = None

        try:
            if options is not None and options['merge_stdout_stderr']:
                data['merge_stdout_stderr'] = 1
            else:
                data['merge_stdout_stderr'] = 0
        except KeyError:
            data['merge_stdout_stderr'] = None

        try:
            data['result_stdout'] = lg['stdout']
        except KeyError:
            data['result_stdout'] = None

        try:
            data['result_stderr'] = lg['stderr']
        except KeyError:
            data['result_stderr'] = None

        #
        # Submit
        #
        payload = {}
        payload['metadata'] = metadata
        payload['data'] = [data]

        data = self._submit_json_data(payload, s, url, httpauth)
        if data is None:
            return None
        if data['status'] is not 0:
            return None

        # Extract ID
        return {'mpi_install_id':data['ids']['mpi_install_id']}

    def _submit_json_data(self, payload, s, url, httpauth=None):
        headers = {}
        headers['content-type'] = 'application/json'

        print "<<<<<<<---------------- Payload (Start) -------------------------->>>>>>"
        print json.dumps(payload, sort_keys=True, indent=4, separators=(',',': '))
        print "<<<<<<<---------------- Payload (End  ) -------------------------->>>>>>"

        r = s.post(url,
                   data=json.dumps(payload),
                   headers=headers,
                   auth=httpauth,
                   verify=False)

        print "<<<<<<<---------------- Response -------------------------->>>>>>"
        print "Result: %d: %s" % (r.status_code, r.headers['content-type'])
        print r.headers
        print r.reason
        print "<<<<<<<---------------- Raw Output (Start) ---------------->>>>>>"
        print r.text
        print "<<<<<<<---------------- Raw Output (End  ) ---------------->>>>>>"

        if r.status_code != 200:
            return None

        return r.json()

    def _extract_param(self, logger, section, parameter):
        found = logger.getLog(section)
        if found is None:
            print "_extract_param: Section (%s) Not Found! [param=%s]" % (section, parameter)
            return None

        try:
            params = found['parameters']
        except KeyError:
            print "_extract_param: Section (%s) did not contain a parameters entry! [param=%s]" % (section, parameter)
            return None
        for p in params:
            if p[0] == parameter:
                return p[1]

    def _get_client_serial(self, session, url, httpauth=None):
        url = url + "/serial"

        headers = {}
        headers['content-type'] = 'application/json'

        payload = {}
        payload['serial'] = 'serial'

        data = self._submit_json_data(payload, session, url, httpauth)
        if data is None:
            return -1

        if data['status'] is not 0:
            return -2

        return data['client_serial']
