# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 12:47:40 2014

@author: Huapu (Peter) Pan
"""

import datetime
import pytz
import time
from BasicPyLib.FiniteState import FiniteStateClass

class __USEasternMarketObject__(object):
    """
    MarketObject is the abstract base class which manages algorithmic trading algorithms
    When initializes it will determine the US Eastern time time zone
    The basic method is run_according_to_market(), which sleeps when market closes
    and runs when market is open from 9:30am to 4pm EST
    inherited classes should overwrite init_obj(), run_algorithm() and destroy_obj()
    """
    def __init__(self):
        """ determine US Eastern time zone depending on EST or EDT """
        if datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EDT':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+4')
        elif datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EST':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+5')   
        else:
            self.USeasternTimeZone = None
            
        self.marketState = FiniteStateClass(stateList = ['sleep', 'run'])
        
    def init_obj(self):
        pass
    
    def run_algorithm(self):
        pass
    
    def destroy_obj(self):
        pass
    
    def run_according_to_market(self, market_start_time = '9:30:00', 
                                market_close_time = '16:00:00'):
        """
        run_according_to_market() will check if market is open every one second
        if market opens, it will first initialize the object and then run the object
        if market closes, it will turn the marketState back to "sleep"
        """
        while (self.marketState.is_state(self.marketState.states.sleep)):
            time.sleep(1)
            currentTime = datetime.datetime.now(self.USeasternTimeZone)
            dataDate = str(currentTime).split(' ')[0]
            startTime = datetime.datetime.strptime(dataDate + ' ' + market_start_time , '%Y-%m-%d %H:%M:%S')
            startTime = startTime.replace(tzinfo = self.USeasternTimeZone)
            endTime = datetime.datetime.strptime(dataDate + ' ' + market_close_time, '%Y-%m-%d %H:%M:%S')
            endTime = endTime.replace(tzinfo = self.USeasternTimeZone)           
    #        print currentTime.hour, currentTime.minute, currentTime.second
            if (self.marketState.is_state(self.marketState.states.sleep) \
            and (currentTime > startTime) and (currentTime < endTime) \
            and currentTime.isoweekday() in range(1, 6)):
                self.marketState.set_state(self.marketState.states.run)
                print 'start to run at: ', currentTime
                self.init_obj()
            while (self.marketState.is_state(self.marketState.states.run)):
                self.run_algorithm()
                currentTime = datetime.datetime.now(self.USeasternTimeZone)
                if (currentTime >= endTime):
                    print "Market is closed at: ", currentTime
                    self.destroy_obj()
                    self.marketState.set_state(self.marketState.states.sleep)     
                    