# -*- coding: utf-8 -*-
"""
Module IBClient, Created on Wed Dec 17 13:04:49 2014

@author: Huapu (Peter) Pan
"""
import datetime, time, pytz

import IBCpp  # IBCpp.pyd is the Python wrapper to IB C++ API
from IBridgePy.IBridgePyBasicLib.quantopian import Security, ContextClass, \
PositionClass, HistClass, create_contract, MarketOrder,create_order, \
OrderClass, same_security
from IBridgePy.IBridgePyBasicLib.IBAccountManager import IBAccountManager
from IBridgePy.IBridgePyBasicLib.MarketManagerBase import __USEasternMarketObject__
from BasicPyLib.FiniteState import FiniteStateClass
    
class TickTrader(IBAccountManager):
    def setup(self, PROGRAM_DEBUG = False, TRADE_DEBUG = True,
              USeasternTimeZone = None, accountCode = 'ALL', minTick = 0.01):
        """
        initialzation of the IBClient
        """
        super(TickTrader, self).setup(PROGRAM_DEBUG = PROGRAM_DEBUG, 
            TRADE_DEBUG = TRADE_DEBUG, USeasternTimeZone = USeasternTimeZone, 
            accountCode = accountCode, minTick = minTick) 
    
    def error(self, errorId, errorCode, errorString):
        """
        print the error messages from IB
        """
        print 'errorId = ' + str(errorId) + ', errorCode = ' + str(errorCode)
        print 'error message: ' + errorString
        
    def nextValidId(self, orderId):

        if (self.PROGRAM_DEBUG):
            print 'next valid order Id = ' + str(orderId)
        self.startingNextValidIdNumber = orderId
        
if __name__ == "__main__":
    a = Security('AAPL')
    a.print_obj()