#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest
from mock import Mock
from mock import patch
from mock import call

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from vnstat import VnStat, VnStatError
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestVnStat(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("vnstat.sh")
    def test_vnstat_get_usage_with_huge_txrx_output_should_raise_fail(
            self, sh):
        # arrange
        interface = VnStat("wwan0")
        return_text = '''version;3
active;1
interface;eth0
nick;eth0
created;1459152201
updated;1459153660
totalrx;9223372036854775807
totaltx;0
currx;172246839
curtx;1704694
totalrxk;857
totaltxk;4
btime;1458897060
d;0;1459152201;0;0;857;4;1
d;1;0;0;0;0;0;0
d;2;0;0;0;0;0;0
d;3;0;0;0;0;0;0
d;4;0;0;0;0;0;0
d;5;0;0;0;0;0;0
d;6;0;0;0;0;0;0
d;7;0;0;0;0;0;0
'''
        sh.vnstat = Mock(return_value=return_text)

        # act and assert
        with self.assertRaises(VnStatError):
            interface.get_usage()

        # more asserts
        self.assertEquals(
            sh.vnstat.call_args_list,
            [
                call("-i", "wwan0", "--dumpdb"),
                call("-i", "wwan0", "--delete", "--force")
            ]
        )

        self.assertEquals(
            sh.service.call_args_list,
            [
                call('vnstat', 'stop'),
                call('vnstat', 'start')
            ]
        )


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
