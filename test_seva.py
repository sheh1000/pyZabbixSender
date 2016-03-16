from pyZabbixSender.sy import syZabbixSender

# this import is optional. Here is used to create a timestamp to associate
# to some data points, for example/testing purposes only.
import time

# Specifying server, but using default port
z = syZabbixSender("95.79.44.111")

def printBanner(text):
    border_char = '#'
    border = border_char * (len(text) + 4)
    print "\n\n%s" % border
    print "%s %s %s" % (border_char, text, border_char)
    print border
    
    
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
    results = z.sendDataOneByOne()

    # You'll get a "results" like:
    #[ (0, {'host': 'test_host', 'value': 21, 'key': 'test_trap'})
    #  (1, {'host': 'test_host', 'value': 100, 'key': 'test_trap1'})
    #]
    print "---- Results content:"
    print results
    
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
    
    results = z.sendData(max_data_per_conn=3)
    print "---- Results content:"
    print results


def test_03():
    '''
    Testing method "sendSingle"
    '''
    printBanner("test_03")

    # We don't need to clean internal data, because we'll send data given to the method
    
    # Sending data right now, without timestamp
    result = z.sendSingle("local.seva.test", "test", 1)
    
    print "---- After sendSingle without timestamp"
    print result
    
    # Now sending data with timestamp
    result = z.sendSingle("local.seva.test", "test", 1, int(round(time.time())))
    print "\n---- After sendSingle with timestamp"
    print result
    

def test_04():
    '''
    Testing getData method.
    '''
    printBanner("test_04")
    
    # Just ensuring we start without data, in case other example was
    # executed before this one
    z.clearData()
    
    # Adding data
    z.addData("local.seva.test", "test", 1)
    z.addData("local.seva.test", "test", 2)
    
    # Showing current data
    print "---- Showing stored data:"
    print z
    
    # remember that getData returns a copy of the data
    copy_of_data = z.getData()
    print "\n---- Showing data returned:"
    print copy_of_data
    
    # We'll modify returned data, to show this won't affect internal data
    print "\n---- Modifying returned data"
    copy_of_data.append({'host': 'local.seva.test', 'value': 500, 'key': 'test'})

    # Showing current data
    print "\n---- Showing stored data again (note is the same as before):"
    print z

    print "\n---- Showing returned and modified data:"
    print copy_of_data
    
    
        
# Here you can execute the test/examples you want
test_01()
test_02()
test_03()
test_04()