#
#   server.py | an http server wrapping the IBGateway API
#   -----------------------------------------------------
#   Sept 2011 | jesse dot tane at gmail dot com
#   
#   URLs
#   ----
#   GET /history  symbol=ABC  &  symbol=123  &  date=UTC_SECONDS  & field=TRADES & rth=0
#

import os
import sys
parent = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.insert(0, parent)

import pdb
import math
import time
import json
import threading
from pytz import timezone
from datetime import datetime
import util.commandLineUI as ui
from util.tws import Tws as TwsWrapper
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import urllib.parse as parse

# IB TWS libs
from ib.ext.ComboLeg import ComboLeg
from ib.ext.Contract import Contract
from ib.ext.ExecutionFilter import ExecutionFilter
from ib.ext.Order import Order
from ib.ext.ScannerSubscription import ScannerSubscription
from ib.lib.logger import logger as basicConfig
from ib.opt import ibConnection, message


# globals
# -------

tws = None
server = None
historicalData = {}
lock = threading.RLock()


# A multithreaded HTTPServer
# --------------------------

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """ Threaded version """
    
class Handler(BaseHTTPRequestHandler):
    
    urls = {
        "/history" : "history"
    }
    
    # entry point for an inbound request
    def do_GET(self):
        
        url = self.path.split("?")
        urls = self.__class__.urls
        notFound = True
        for u in urls:
            if u == url[0]:
                notFound = False
                if len(url) > 1: self.processParams(url[1])
                else: self.params = {}
                getattr(self, urls[u])()
        
        if notFound:
            self.send_error(404, "Resource not found")
            return
    
    #
    def processParams(self, qs):
        self.params = params = parse.parse_qs(qs)
        for p in params:
            if type(params[p]) == list and len(params[p]) == 1:
                params[p] = params[p][0]
    
    #
    def history(self):
        params = self.params
        try:
            symbols = params["symbol"]
            date = float(params["date"])
            endDateTime = time.strftime("%Y%m%d %H:%M:%S", time.gmtime(date + 86400))
            duration = "1 D"
            barSize = "30 secs"
            whatToShow = params["field"].upper() #"TRADES" #"ASK" #"BID"
            dateFormat = 2  # UTC seconds
            rth = "0"       # show after hours
        except:
            self.send_error(404, "Missing parameters")
            return

        def genErrorHandler(stid):
            def eh(msg):
                historicalData[stid].set()
            tws.con.register(eh, "Error")
            return eh

        def reqFromTws(symbol):
            tid = tws.genTID()
            stid = str(tid)
            historicalData[tid] = []
            historicalData[stid] = event = threading.Event()
            historicalData[stid + "eh"] = eh = genErrorHandler(stid)
            tws.con.reqHistoricalData(tid, tws.makeContract(symbol), endDateTime, duration, barSize, whatToShow, rth, dateFormat)

            print("Historical data requested for " + symbol + ", waiting for tws...");
            event.wait()
            tws.con.cancelHistoricalData(tid)
            tws.con.unregister(historicalData[stid + "eh"], "Error")

            #print(historicalData[tid][0]) # int reqId, String date, double open, double high, double low, double close, int volume, int count, double WAP, boolean hasGaps
            d = data["data"]
            for h in historicalData[tid]:
                d.append({
                    "date"  : h.date,
                    "open"  : h.open,
                    "high"  : h.high,
                    "low"   : h.low,
                    "close" : h.close,
                    "volume": h.volume,
                    "count" : h.count,
                    "WAP"   : h.WAP,
                })
            del historicalData[tid]
            del historicalData[str(tid)]

        tzoffset = offsetForTimeInZone(date, "US/Eastern")  # get offset to market local time, in this case US/Eastern for New York
        data = { "tzoffset" : tzoffset, "data" : [] }
        if type(symbols) != list: reqFromTws(symbols)
        else: reqFromTws(symbols[0])
        
        print("DEBUG")
        print(whatToShow)
        print(symbols)
        print(date)
        print(endDateTime)
        print("entries - " + str(len(data["data"])))
        print("")
        
        #if len(data["data"]) > 0: self.send_response(200)
        #else: self.send_response(404)
        
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(bytearray(json.dumps(data), "utf8"))


# IB TWS handlers (the action)
# ----------------------------

#
class Tws(TwsWrapper):
    
    #
    def onConnect(self):
        self.con.register(onError, "Error")
        self.con.register(onHistoricalData, "HistoricalData")
        
    #
    def onDisconnect(self):
        self.con.unregister(onError, "Error")
        self.con.unregister(onHistoricalData, "HistoricalData")

#
def onError(msg):
    print(msg)

#
def onHistoricalData(msg):
    if msg.date.find("finished") > -1: historicalData[str(msg.reqId)].set()
    elif msg.reqId in historicalData: historicalData[msg.reqId].append(msg)


# General app functions
# ---------------------

#
def twsInit(clientId=None):
    global tws
    tws = Tws(clientId)
    tws.connect()

#
def serverInit(port=2503, handler=Handler):
    
    def serve():
        s = ThreadedHTTPServer(("", port), handler)
        s.daemon_threads = True
        while ui.running:
            s.handle_request()
    
    global server
    server = threading.Thread(target=serve)
    server.daemon = True
    server.start()

#
def offsetForTimeInZone(date, zone):
    d = datetime.utcfromtimestamp(date)                 # create datetime object from a utc timestamp
    d = timezone("UTC").localize(d)                     # add UTC tzinfo object
    d = d.astimezone(timezone(zone))                    # convert to the requested timezone
    off = d.utcoffset()                                 
    if off.days == 0: secs = -off.seconds
    else: secs = 86400-off.seconds
    return { "seconds" : secs, "string" : d.strftime("%z") }

#
def debug():
    print("That tickles!")

#
def quit():
    ui.running = False
    if tws and tws.connected():
        tws.disconnect()
    print("Bye!")
    time.sleep(0.5)
    sys.exit()
    
    
# entry point

if __name__ == '__main__':

    # welcome!
    print("\nHISTORICAL DATA SERVER!")
    print("-----------------------\n")

    # set up cmd line ui
    ui.bind("d", debug)
    ui.bind("q", quit)
    ui.start()
    
    # do it up
    twsInit(2503)
    serverInit(2503)
    
    # bind tws specific handlers
    ui.bind("x", tws.disconnect)
    ui.bind("r", tws.reconnect)
    ui.bind("s", tws.connected)
    
    # this seems silly...
    while ui.running:
        time.sleep(0.25)
    