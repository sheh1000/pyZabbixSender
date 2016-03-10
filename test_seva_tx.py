from txZabbixSender import txZabbixSender

# this import is optional. Here is used to create a timestamp to associate
# to some data points, for example/testing purposes only.
import time
import sys

from twisted.internet import reactor, defer

from twisted.python import log
log.startLogging(sys.stdout,False)

# Specifying server, but using default port
z = txZabbixSender("95.79.44.111")

def printBanner(text):
    border_char = '#'
    border = border_char * (len(text) + 4)
    print "\n\n%s" % border
    print "%s %s %s" % (border_char, text, border_char)
    print border
    
    
@defer.inlineCallbacks
def tests():

    
    yield test_01()
    yield test_02()
    yield test_03()
    reactor.stop()

@defer.inlineCallbacks
def test_01():
    '''
    Simple "debugging" usage example (using "sendDataOneByOne" method)
    '''
    printBanner("test_01")
    
    # Just ensuring we start without data, in case other example was
    # executed before this one
    z.clearData()

    # Adding a host/trap that exist
    z.addData("local.seva.test", "test", 21)

    # Adding a host that exist, but a trap that doesn't
    z.addData("local.seva.test", "test1", 100)

    # Sending stored data, one by one, to know which host/traps have problems
    results = yield z.sendDataOneByOne()

    # You'll get a "results", note that they differ from sync code!
    print "---- Results content:"
    print results

@defer.inlineCallbacks
def test_02():
    '''
    Testing "max_data_per_conn" parameter in "sendData" method
    '''
    printBanner("test_02")
    
    # Just ensuring we start without data, in case other example was
    # executed before this one
    z.clearData()

    # Adding some valid data
    for i in range (10):
        z.addData("local.seva.test", "test", i)
        
    # Now adding a trap that doesn't exist in the server
    z.addData("local.seva.test", "test1", 3)
    
    results = yield z.sendData(max_data_per_conn=3)
    
    # Now lets take a look at the return.
    # You'll get a "results", note that they differ from sync code!
    print "---- Results content:"
    print results


@defer.inlineCallbacks
def test_03():
    '''
    Testing method "sendSingle"
    '''
    printBanner("test_03")

    # We don't need to clean internal data, because we'll send data given to the method
    
    # Sending data right now, without timestamp
    result = yield z.sendSingle("local.seva.test", "test", 1)
    
    print "---- After sendSingle without timestamp"
    print result
    
    # Now sending data with timestamp
    result = yield z.sendSingle("local.seva.test", "test", 1, int(round(time.time())))
    print "\n---- After sendSingle with timestamp"
    print result
    


# Here you can execute the test/examples you want
reactor.callWhenRunning(tests)
reactor.run()
