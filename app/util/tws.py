#
#   tws.py | a simple wrapper around tws to be subclassed
#   -----------------------------------------------------
#   Sept 2011 | jesse dot tane at gmail com
#


#
import time

# IB TWS libs
from ib.ext.ComboLeg import ComboLeg
from ib.ext.Contract import Contract
from ib.ext.ExecutionFilter import ExecutionFilter
from ib.ext.Order import Order
from ib.ext.ScannerSubscription import ScannerSubscription
from ib.lib.logger import logger as basicConfig
from ib.opt import ibConnection, message

#
class Tws:
    
    #
    def __init__(self, clientId):
        self.clientId = clientId
        self.con = ibConnection("localhost", 4001, clientId)

    #
    def connect(self):
        self.con.connect()
        self.onConnect()
        if self.connected():
            print("Tws connected")
        
    #
    def disconnect(self):
        self.onDisconnect()
        self.con.disconnect()
        if self.connected() == False:
            print("Tws disconnected")
    
    #
    def connected(self):
        return self.con.isConnected()
    
    #
    def reconnect(self):
        self.disconnect()
        time.sleep(1)
        self.connect()
    
    #
    def genTID(self):
        try: self.tid += 1
        except: self.tid = 0
        return self.tid

    #
    def makeContract(self, symbol):
        c = Contract()
        c.m_symbol = symbol
        c.m_secType = "STK"
        c.m_currency = "USD"
        c.m_exchange = "SMART"
        return c

    #
    def makeScannerSubscription(self, code, limit):
        sub = ScannerSubscription()
        sub.numberOfRows(limit)
        sub.instrument("STK")
        sub.scanCode(code)
        sub.locationCode("STK.US.MAJOR")
        return sub
