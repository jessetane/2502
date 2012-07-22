#
#   commandLineUI.py | an interactive command line handler for Py3k
#   ---------------------------------------------------------------
#   July 2010 | jesse dot tane at gmail com
#

import sys
import signal
import threading

# starts the command line
def start():
    thread.start()

# ends the command line
def end(signum=None, frame=None):
    global running
    if commands["q"] == end: running = False
    else: commands["q"]()

# binds a command to a handler function
def bind(commandString, handler):
    commands[commandString] = handler

# binds all commands to a generic handler
def bindAll(handler):
    global generic
    generic = handler

# main loop
def main():
    while running:
        userinput = sys.stdin.readline()[:-1]
        if generic != None: generic(userinput)
        try: commands[userinput]()
        except KeyError: print("Command \"" + userinput + "\" not found!")


running = True
commands = {}
generic = None
bind("q", end)
signal.signal(signal.SIGINT, end)
thread = threading.Thread(target=main)
thread.daemon = True