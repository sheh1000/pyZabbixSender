# -*- coding: utf-8
# Copyleft 2016 Vsevolod Novikov <nnseva (at) gmail(dot)com>
# > Based on work by Kurt Momberg <kurtqm (at) yahoo(dot)com(dot)ar>
# >> Based on work by Klimenko Artyem <aklim007(at)gmail(dot)com>
# >>> Based on work by Rob Cherry <zsend(at)lxrb(dot)com>
# >>>> Based on work by Enrico Tröger <enrico(dot)troeger(at)uvena(dot)de>
# License: GNU GPLv2

import socket
import struct
import time
import sys
import re

from pyZabbixSenderBase import *

class syZabbixSender(pyZabbixSenderBase):
    '''
    This class allows you to send data to a Zabbix server, using the same
    protocol used by the zabbix_server binary distributed by Zabbix.

    It uses exceptions to report errors.
    '''

    FAILED_COUNTER = re.compile('^.*failed.+?(\d+).*$')
    PROCESSED_COUNTER = re.compile('^.*processed.+?(\d+).*$')
    SECONDS_SPENT = re.compile('^.*seconds spent.+?((-|\+|\d|\.|e|E)+).*$')

    def send_packet(self, packet):
        '''
        This is the method that actually sends the data to the zabbix server.
        '''
        mydata = json.dumps(packet)
        socket.setdefaulttimeout(self.timeout)
        data_length = len(mydata)
        data_header = str(struct.pack('q', data_length))
        data_to_send = 'ZBXD\1' + str(data_header) + str(mydata)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.zserver, self.zport))
        sock.send(data_to_send)

        response_header = sock.recv(5)
        if not response_header == 'ZBXD\1':
            raise InvalidResponse('Wrong magic: %s' % response_header)

        response_data_header = sock.recv(8)
        response_data_header = response_data_header[:4]
        response_len = struct.unpack('i', response_data_header)[0]
        response_raw = sock.recv(response_len)
        sock.close()
        response = json.loads(response_raw)
        failed = self.FAILED_COUNTER.match(response['info'].lower() if 'info' in response else '')
        processed = self.PROCESSED_COUNTER.match(response['info'].lower() if 'info' in response else '')
        seconds_spent = self.SECONDS_SPENT.match(response['info'].lower() if 'info' in response else '')
        if failed is None or processed is None:
            raise InvalidResponse('Unable to parse server response',packet,response)
        failed = int(failed.group(1))
        processed = int(processed.group(1))
        seconds_spent = float(seconds_spent.group(1)) if seconds_spent else None
        response['info'] = {
            'failed':failed,
            'processed':processed,
            'seconds spent':seconds_spent
        }
        return response

    def sendData(self, packet_clock=None, max_data_per_conn=None):
        '''
        #####Description:
        Sends data stored using *addData* method, to the Zabbix server.

        #####Parameters:
        * **packet_clock**: [in] [integer] [optional] Zabbix server uses the "clock" parameter in the packet to associate that timestamp to all data values not containing their own clock timestamp. Then:
            * If packet_clock is specified, zabbix server will associate it to all data values not containing their own clock.
            * If packet_clock is **NOT** specified, zabbix server will use the time when it received the packet as packet clock.

         You can create a timestamp compatible with "clock" or "packet_clock" parameters using this code:

              int(round(time.time()))
         *Default value: None*

        * **max_data_per_conn**: [in] [integer] [optional] Allows the user to limit the number of data points sent in one single connection, as some times a too big number can produce problems over slow connections. 

            Several "sends" will be automatically performed until all data is sent.

            If omitted, all data points will be sent in one single connection. *Default value: None*

        Please note that **internal data is not deleted after *sendData* is executed**. You need to call *clearData* after sending it, if you want to remove currently stored data.

        #####Return:
        A list of *(result, msg)* associated to each "send" operation, where *result* is a boolean meaning success of the operation,
        and *msg* is a message from the server in case of success, or exception in case of error.

        In case of success, the server returns a message which is parsed by the function. The server message
        contains counters for *processed* and *failed* (ignored) data items. Note that even if processed
        data counter is 0 and all data items have been failed, it does not mean the error condition.
        '''
        if not max_data_per_conn or max_data_per_conn > len(self._data):
            max_data_per_conn = len(self._data)

        responses = []
        i = 0
        while i*max_data_per_conn < len(self._data):

            sender_data = {
                "request": "sender data",
                "data": [],
            }
            if packet_clock:
                sender_data['clock'] = packet_clock

            sender_data['data'] = self._data[i*max_data_per_conn:(i+1)*max_data_per_conn]
            try:
                response = self.send_packet(sender_data)
            except Exception,ex:
                responses.append((False,ex))
            else:
                responses.append((True,response))
            i += 1

        return responses

    def sendDataOneByOne(self):
        '''
        #####Description:
        You can use this method to send all stored data, one by one, to determine which traps are not being handled correctly by the server.

        Using this method you'll be able to detect things like:
        * hosts not defined in the server
        * traps not defined in some particular host

        This is primarily intended for debugging purposes.

        #####Parameters:
        None

        #####Return:
        A list of *(result, msg)* associated to each "send" operation, where *result* is a boolean meaning success of the operation,
        and *msg* is a message from the server in case of success, or exception in case of error.

        In case of success, the server returns a message which is parsed by the function. The server message
        contains counters for *processed* and *failed* (ignored) data items. Note that even if processed
        data counter is 0 and all data items have been failed, it does not mean the error condition.
        '''
        return self.sendData(max_data_per_conn=1)

    def sendSingle(self, host, key, value, clock=None):
        '''
        #####Description:
        Instead of storing data for sending later, you can use this method to send specific values right now.

        #####Parameters:
        It shares the same parameters as the *addData* method.
        * **host**: [in] [string] [mandatory] The host which the data is associated to.
        * **key**: [in] [string] [mandatory] The name of the trap associated to the host in the Zabbix server.
        * **value**: [in] [any] [mandatory] The value you want to send. Please note that you need to take care about the type, as it needs to match key definition in the Zabbix server. Numeric types can be specified as number (for example: 12) or text (for example: "12").
        * **clock**: [in] [integer] [optional] Here you can specify the Unix timestamp associated to your measurement. For example, you can process a log or a data file produced an hour ago, and you want to send the data with the timestamp when the data was produced, not when it was processed by you. If you don't specify this parameter, zabbix server will assign a timestamp when it receives the data.

            You can create a timestamp compatible with "clock" parameter using this code:
              int(round(time.time()))

            *Default value: None*

        #####Return:
        A message returned by the server.
        '''
        sender_data = {
            "request": "sender data",
            "data": [],
        }

        obj = self._createDataPoint(host, key, value, clock)
        sender_data['data'].append(obj)
        return self.send_packet(sender_data)

    def sendSingleLikeProxy(self, host, key, value, clock=None, proxy=None):
        '''
        #####Description:
        Use this method to put the data for host monitored by proxy server. This method emulates proxy protocol and data will be accepted by Zabbix server
        even if they were send not actually from proxy.

        #####Parameters:
        * **host**: [in] [string] [mandatory] The host which the data is associated to.
        * **key**: [in] [string] [mandatory] The name of the trap associated to the host in the Zabbix server.
        * **value**: [in] [any] [mandatory] The value you want to send. Please note that you need to take care about the type, as it needs to match key definition in the Zabbix server. Numeric types can be specified as number (for example: 12) or text (for example: "12").
        * **clock**: [in] [integer] [optional] Here you can specify the Unix timestamp associated to your measurement. For example, you can process a log or a data file produced an hour ago, and you want to send the data with the timestamp when the data was produced, not when it was processed by you. If you don't specify this parameter, zabbix server will assign a timestamp when it receives the data.

            You can create a timestamp compatible with "clock" parameter using this code:
              int(round(time.time()))

            *Default value: None*

        * **proxy**: [in] [string] [optional] The name of the proxy to be recognized by the Zabbix server. If proxy is not specified, a normal "sendSingle" operation will be performed. *Default value: None*
        #####Return:
        A message returned by the server.
        '''
        # Proxy was not specified, so we'll do a "normal" sendSingle operation
        if proxy is None:
            return sendSingle(host, key, value, clock)

        sender_data = {
            "request": "history data",
            "host": proxy,
            "data": [],
        }

        obj = self._createDataPoint(host, key, value, clock)
        sender_data['data'].append(obj)
        return self.send_packet(sender_data)

#####################################
# --- Examples of usage ---
#####################################
#
# Initiating a pyZabbixSender object -
# z = pyZabbixSender() # Defaults to using ZABBIX_SERVER,ZABBIX_PORT
# z = pyZabbixSender(verbose=True) # Prints all sending failures to stderr
# z = pyZabbixSender(server="172.0.0.100",verbose=True)
# z = pyZabbixSender(server="zabbix-server",port=10051)
# z = pyZabbixSender("zabbix-server", 10051)

# --- Adding data to send later ---
# Host, Key, Value are all necessary
# z.addData("test_host","test_trap","12")
#
# Optionally you can provide a specific timestamp for the sample
# z.addData("test_host","test_trap","13",1365787627)
#
# If you provide no timestamp, you still can assign one when sending, or let
# zabbix server to put the timestamp when the message is received.

# --- Printing values ---
# Not that useful, but if you would like to see your data in tuple form:
# z.printData()

# --- Sending data ---
#
# Just sending a single data point (you don't need to call add_value for this
# to work):
# z.sendSingle("test_host","test_trap","12")
#
# Sending everything at once, with no concern about
# individual item failure -
#
# result = z.sendData()
# for r in result:
#     print "Result: %s -> %s" % (str(r[0]), r[1])
#
# If you're ok with the result, you can delete the data inside the sender, to
# allow a new round of data feed/send.
# z.clearData()
#
# If you want to specify a timestamp to all values without one, you can specify
# the packet_clock parameter:
# z.sendData(packet_clock=1365787627)
#
# When you're sending data over a slow connection, you may find useful the
# possibility to send data in packets with no more than max_data_per_conn
# data points on it.
# All the data will be sent, but in smaller packets.
# For example, if you want to send 4000 data points in packets containing no
# more than 200 of them:
#
# results = z.sendData(max_data_per_conn=200)
# for partial_result in results:
#     print partial_result
#
# Sending every item individually so that we can capture
# success or failure
#
# results = z.sendDataOneByOne()
# for (code,data) in results:
#   if code != z.RC_OK:
#      print "Failed to send: %s" % str(data)
#
#
#####################################
# Mini example of a working program #
#####################################
#
# import sys
# sys.path.append("/path/to/pyZabbixSender.py")
# from pyZabbixSender import pyZabbixSender
#
# z = pyZabbixSender() # Defaults to using ZABBIX_SERVER, ZABBIX_PORT
# z.addData("test_host","test_trap_1","12")
# z.addData("test_host","test_trap_2","13",1366033479)
# 
# Two ways of printing internal data
# z.printData()
# print z
#
# results = z.sendDataOneByOne()
# for (code,data) in results:
#   if code != z.RC_OK:
#      print "Failed to send: %s" % str(data)
# z.clearData()
#####################################
