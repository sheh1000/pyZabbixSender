# -*- coding: utf-8
# Copyright 2015 Kurt Momberg <kurtqm (at) yahoo(dot)com(dot)ar>
# > Based on work by Klimenko Artyem <aklim007(at)gmail(dot)com>
# >> Based on work by Rob Cherry <zsend(at)lxrb(dot)com>
# >>> Based on work by Enrico Tröger <enrico(dot)troeger(at)uvena(dot)de>
# License: GNU GPLv2

import struct
import time
import sys
import re

# If you're using an old version of python that don't have json available,
# you can use simplejson instead: https://simplejson.readthedocs.org/en/latest/
#import simplejson as json
import json

class pyZabbixSenderBase:
    '''
    This class creates network-agnostic data structures to send data to a Zabbix server
    '''
    ZABBIX_SERVER = "127.0.0.1"
    ZABBIX_PORT   = 10051

    def __init__(self, server=ZABBIX_SERVER, port=ZABBIX_PORT, verbose=False):
        '''
        #####Description:
        This is the constructor, to obtain an object of type pyZabbixSender, linked to work with a specific server/port.

        #####Parameters:
        * **server**: [in] [string] [optional] This is the server domain name or IP. *Default value: "127.0.0.1"*
        * **port**: [in] [integer] [optional] This is the port open in the server to receive zabbix traps. *Default value: 10051*
        * **verbose**: [in] [boolean] [optional] This is to allow the library to write some output to stderr when finds an error. *Default value: False*

        **Note: The "verbose" parameter will be revisited and could be removed/replaced in the future**

        #####Return:
        It returns a pyZabbixSender object.
        '''
        self.zserver = server
        self.zport   = port
        self.verbose = verbose
        self.timeout = 5         # Socket connection timeout.
        self._data = []         # This is to store data to be sent later.


    def __str__(self):
        '''
        This allows you to obtain a string representation of the internal data
        '''
        return str(self._data)


    def _createDataPoint(self, host, key, value, clock=None):
        '''
        Creates a dictionary using provided parameters, as needed for sending this data.
        '''
        obj = {
            'host': host,
            'key': key,
            'value': value,
        }
        if clock:
            obj['clock'] = clock
        return obj

    def addData(self, host, key, value, clock=None):
        '''
        #####Description:
        Adds host, key, value and optionally clock to the internal list of data to be sent later, when calling one of the methods to actually send the data to the server.

        #####Parameters:
        * **host**: [in] [string] [mandatory] The host which the data is associated to.
        * **key**: [in] [string] [mandatory] The name of the trap associated to the host in the Zabbix server.
        * **value**: [in] [any] [mandatory] The value you want to send. Please note that you need to take care about the type, as it needs to match key definition in the Zabbix server. Numeric types can be specified as number (for example: 12) or text (for example: "12").
        * **clock**: [in] [integer] [optional] Here you can specify the Unix timestamp associated to your measurement. For example, you can process a log or a data file produced an hour ago, and you want to send the data with the timestamp when the data was produced, not when it was processed by you. If you don't specify this parameter, zabbix server will assign a timestamp when it receives the data.

            You can create a timestamp compatible with "clock" parameter using this code:
              int(round(time.time()))

            *Default value: None*

        #####Return:
        This method doesn't have a return.
        '''
        obj = self._createDataPoint(host, key, value, clock)
        self._data.append(obj)


    def clearData(self):
        '''
        #####Description:
        This method removes all data from internal storage. You need to specify when it's done, as it's not automatically done after a data send operation.

        #####Parameters:
        None

        #####Return:
        None
        '''
        self._data = []


    def getData(self):
        '''
        #####Description:
        This method is used to obtain a copy of the internal data stored in the object.

        Please note you will **NOT** get the internal data object, but a copy of it, so no matter what you do with your copy, internal data will remain safe.

        #####Parameters:
        None

        #####Return:
        A copy of the internal data you added using the method *addData* (an array of dicts).
        '''
        copy_of_data = []
        for data_point in self._data:
            copy_of_data.append(data_point.copy())
        return copy_of_data


    def printData(self):
        '''
        #####Description:
        Print stored data (to stdout), so you can see what will be sent if "sendData" is called. This is useful for debugging purposes.

        #####Parameters:
        None

        #####Return:
        None
        '''
        for elem in self._data:
            print str(elem)
        print 'Count: %d' % len(self._data)


    def removeDataPoint(self, data_point):
        '''
        #####Description:
        This method delete one data point from the internal stored data. 

        It's main purpose is to narrow the internal data to keep only those failed data points (those that were not received/processed by the server) so you can identify/retry them. Data points can be obtained from *sendDataOneByOne* return, or from *getData* return.

        #####Parameters:
        * **data_point**: [in] [dict] [mandatory] This is a dictionary as returned by *sendDataOneByOne()* or *getData* methods.

        #####Return:
        It returns True if data_point was found and deleted, and False if not.
        '''
        if data_point in self._data:
            self._data.remove(data_point)
            return True

        return False
