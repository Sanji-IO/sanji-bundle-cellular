#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging

from sanji.core import Sanji
from sanji.connection.mqtt import Mqtt


REQ_RESOURCE = "/network/cellulars"


class View(Sanji):

    # This function will be executed after registered.
    def run(self):

        print "Go Test 1"
        res = self.publish.get(REQ_RESOURCE)
        if res.code != 200:
            print "GET should reply code 200"
            self.stop()
        else:
            print res.to_json()
        print "Pass 1 Test"

        print "Go Test 2"
        res = self.publish.get(REQ_RESOURCE+'/0')
        if res.code != 200:
            print "GET should reply code 200"
            self.stop()
        else:
            print res.to_json()
        print "Pass 2 Test"

        print "Go Test 3"
        res = self.publish.get(REQ_RESOURCE+'/5')
        if res.code == 200:
            print "GET should reply code 400"
            self.stop()
        else:
            print res.to_json()
        print "Pass 3 Test"

        print "Go Test 4"
        res = self.publish.put(REQ_RESOURCE+'/0',
                               data={"enable": 1,
                                     "apn": "internet"})
        if res.code != 200:
            print "GET should reply code 200"
            print res.to_json()
            self.stop()
        else:
            print res.to_json()
        print "Pass 4 Test"

        # print "Go Test 5"
        res = self.publish.put(REQ_RESOURCE+'/0',
                               data={"enable": 0,
                                     "apn": "internet"})
        if res.code != 200:
            print "GET should reply code 200"
            self.stop()
        else:
            print res.to_json()
        print "Pass 5 Test"

        # stop the test view
        self.stop()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Cellular")

    view = View(connection=Mqtt())
    view.start()
