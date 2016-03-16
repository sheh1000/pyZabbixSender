# -*- coding: utf-8
# Copyleft 2016 Vsevolod Novikov <nnseva (at) gmail(dot)com>
# > Based on work by Kurt Momberg <kurtqm (at) yahoo(dot)com(dot)ar>
# >> Based on work by Klimenko Artyem <aklim007(at)gmail(dot)com>
# >>> Based on work by Rob Cherry <zsend(at)lxrb(dot)com>
# >>>> Based on work by Enrico Tröger <enrico(dot)troeger(at)uvena(dot)de>
# License: GNU GPLv2

from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor,address,defer

from twisted.python import log, failure

from twisted.internet import protocol, reactor
from zope.interface import implements
from twisted.internet import interfaces,error

import struct
import time
import sys
import re

from pyZabbixSenderBase import *

class SenderProtocol(protocol.Protocol):
    def __init__(self,factory):
        self.factory = factory
        self.reset()

    def reset(self):
        self.tail = ''
        self.state = 'magic'

    def dataReceived(self, data):
        log.msg("RECEIVED DATA: %s" % len(data))
        while len(data):
            l = self.parseData(data)
            log.msg("PARSED DATA: %s" % l)
            if l:
                data = data[l:]
            else:
                self.error_happens(failure.Failure(InvalidResponse("Unknown data chunk")))
                self.transport.loseConnection()
                break

    def parseData(self,data):
        d = self.tail + data
        l = self._expected_length()
        if len(d) < l:
            self.tail = d
            return len(data)

        self._expected_parse(d[0:l])
        taill = len(self.tail)
        self.tail = ''
        return l - taill

    def _expected_length(self):
        m = getattr(self,'_expected_length_'+self.state)
        return m()

    def _expected_parse(self,data):
        m = getattr(self,'_expected_parse_'+self.state)
        return m(data)

    def _expected_length_magic(self):
        return 5

    def _expected_parse_magic(self,data):
        if not data == 'ZBXD\1':
            self.error_happens(failure.Failure(InvalidResponse("Wrong magic: %s" % data)))
            self.transport.loseConnection()
            return
        self.state = 'header'

    def _expected_length_header(self):
        return 8

    def _expected_parse_header(self,data):
        self._data_length, = struct.unpack('i',data[:4])
        log.msg("Received length: %s" % self._data_length)
        self.state = 'data'

    def _expected_length_data(self):
        return self._data_length

    def _expected_parse_data(self,data):
        packet = {}
        self.state = 'header'
        try:
            packet = json.loads(data)
        except Exception,ex:
            f = failure.Failure()
            self.error_happens(f)
            self.transport.loseConnection()
            return
        log.msg("Received packet: %s" % packet)
        try:
            self.packet_received(packet)
        except Exception,ex:
            f = failure.Failure()
            self.error_happens(f)
            self.transport.loseConnection()
            return
        self.state = 'done'
        self.transport.loseConnection() # Normally the Zabbix expects closing connection from the sender

    def packet_received(self,packet):
        raise NotImplemented()

    def error_happens(self,fail):
        log.err(fail)

    def send_packet(self,packet):
        '''sends a packet in form of json'''
        log.msg("Sending a packet: %s" % packet)
        try:
            data = json.dumps(packet)
        except Exception,ex:
            f = failure.Failure()
            self.error_happens(f)
            self.transport.loseConnection()
            return
        data_length = len(data)
        data_header = str(struct.pack('q', data_length))
        data_to_send = 'ZBXD\1' + str(data_header) + data
        self.transport.write(data_to_send)
        log.msg("Packet sent: %s bytes" % len(data_to_send))

class SenderProcessor(SenderProtocol):
    def __init__(self,factory,packet,deferred):
        SenderProtocol.__init__(self,factory)
        self.deferred = deferred
        self.packet = packet

    def connectionMade(self):
        self.send_packet(self.packet)
    def packet_received(self,packet):
        response = recognize_response(packet)
        self.deferred.callback(response)
    def error_happens(self,fail):
        self.deferred.errback(fail)

class SenderFactory(protocol.ClientFactory):
    def __init__(self,packet,deferred):
        self.deferred = deferred
        self.packet = packet
    def buildProtocol(self,addr):
        return SenderProcessor(self,self.packet,self.deferred)

    def clientConnectionFailed(self, connector, reason):
        if not self.deferred.called:
            log.err("ERROR: connecting has been failed because of:%s, sending data has been skipped" % reason)
            self.deferred.errback(reason)

    def clientConnectionLost(self, connector, reason):
        if not isinstance(reason.value,error.ConnectionDone):
            if not self.deferred.called:
                log.err("ERROR: connecting has been lost because of:%s, sending data has been skipped" % reason)
                self.deferred.errback(reason)

class txZabbixSender(pyZabbixSenderBase):
    '''
    This class allows you to send data to a Zabbix server asynchronously, using the same
    protocol used by the zabbix_server binary distributed by Zabbix.
    '''

    def _send(self,packet):
        '''This method creates a connection, sends data and returns deferred to get a result'''
        deferred = defer.Deferred()
        connection = reactor.connectTCP(self.zserver,self.zport,SenderFactory(packet,deferred),self.timeout)
        return deferred

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
        A deferred list of each "send" operation results.
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
            response = self._send(sender_data)
            responses.append(response)
            i += 1

        return defer.DeferredList(responses)

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
        A deferred list of each "send" operation results.
        '''
        retarray = []
        for i in self._data:
            if 'clock' in i:
                d = self.sendSingle(i['host'], i['key'], i['value'], i['clock'])
            else:
                d = self.sendSingle(i['host'], i['key'], i['value'])

            retarray.append(d)
        return defer.DeferredList(retarray)


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
        A deferred for the operation results.
        '''
        sender_data = {
            "request": "sender data",
            "data": [],
        }

        obj = self._createDataPoint(host, key, value, clock)
        sender_data['data'].append(obj)
        return self._send(sender_data)


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
        A deferred for the operation results.
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
        return self._send(sender_data)
