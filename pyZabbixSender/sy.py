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
        return recognize_response_raw(response_raw)

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
