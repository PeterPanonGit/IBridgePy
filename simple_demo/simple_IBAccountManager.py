# -*- coding: utf-8 -*-
"""
Created on Sat Jan 03 08:35:42 2015

@author: Huapu (Peter) Pan
"""
import datetime
from IBridgePy.IBridgePyBasicLib.IBAccountManager import IBAccountManager

if __name__ == "__main__":
    port = 7496; clientID = 1
    c = IBAccountManager()  # create a client object
    c.setup();      # additional setup. It's optional.
    c.connect("", port, clientID) # you need to connect to the server before you do anything.
    c.reqCurrentTime()
    while (True):
        if (c.stime is not None and c.stime_previous is None):
            c.stime_previous = c.stime
            print "current system time: ", c.stime, datetime.datetime.now(tz = c.USeasternTimeZone)
        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread.     