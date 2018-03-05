from __future__ import print_function
from builtins import str
#!/usr/bin/env python
#
# Copyright (c) 2015-2018 Intel, Inc. All rights reserved.
# Copyright (c) 2018      Los Alamos National Security, LLC. 
#                         All rights reserved.
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
#

import shutil
import os
from threading import Timer
from BaseMTTUtility import *
import signal

## @addtogroup Utilities
# @{
# @section Watchdog
# @param  timeout  Time in seconds before generating exception
# @}
class Watchdog(BaseMTTUtility):
    def __init__(self, timeout=360, testDef=None):
        BaseMTTUtility.__init__(self)
        self.options = {}
        self.options['timeout'] = (str(timeout), "Time in seconds before generating exception")
        self.timer = None
        self.timeout = int(timeout)
        self.testDef = testDef
        self.activated = False

    def print_name(self):
        return "Watchdog"

    def print_options(self, testDef, prefix):
        lines = testDef.printOptions(self.options)
        for line in lines:
            print(prefix + line)
        return

    # Start the watchdog timer
    def start(self):
        if not self.timer or not self.timer.is_alive():
            self.timer = Timer(self.timeout, self.defaultHandler)
            self.timer.start()

    # Stop the watchdog timer
    def stop(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    # Reset the watchdog timer
    def reset(self):
        self.stop()
        self.start()

    def activate(self):
        if not self.activated:
            IPlugin.activate(self)
            self.activated = True

    # Catch when deactivated to stop the timer thread
    def deactivate(self):
        if self.activated:
            IPlugin.deactivate(self)
            self.stop()
            self.activated = False

    # This function is called when timer runs out of time!
    # Give a SIGINT to parent process to stop execution
    def defaultHandler(self):
        if self.testDef: self.testDef.plugin_trans_sem.acquire()
        os.kill(os.getpid(), signal.SIGINT)

    # Start execution of the plugin from an INI file
    def execute(self, log, keyvals, testDef):
        testDef.logger.verbose_print("Watchdog Execute")
        cmds = {}
        testDef.parseOptions(log, self.options, keyvals, cmds)
        self.testDef = testDef
        try:
            self.timeout = int(cmds['timeout'])
        except ValueError:
            log['status'] = 1
            log['stderr'] = "Could not parse time input from ini file for Watchdog"
        self.start()
        log['status'] = 0
        return
