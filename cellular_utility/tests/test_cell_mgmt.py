#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from cellular_utility.cell_mgmt import CellMgmt
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestCellMgmt(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_start_ip_regex_should_pass(self):
        # arrange
        SUT = (
            "IP=111.70.154.149\n"
            "SubnetMask=255.255.255.252\n"
            "Gateway=111.70.154.150\n"
            "DNS=168.95.1.1 168.95.192.1\n")

        # act
        match = CellMgmt._start_ip_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("111.70.154.149", match.group(1))

    def test_start_netmask_regex_should_pass(self):
        # arrange
        SUT = (
            "IP=111.70.154.149\n"
            "SubnetMask=255.255.255.252\n"
            "Gateway=111.70.154.150\n"
            "DNS=168.95.1.1 168.95.192.1\n")

        # act
        match = CellMgmt._start_netmask_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("255.255.255.252", match.group(1))

    def test_start_gateway_regex_should_pass(self):
        # arrange
        SUT = (
            "IP=111.70.154.149\n"
            "SubnetMask=255.255.255.252\n"
            "Gateway=111.70.154.150\n"
            "DNS=168.95.1.1 168.95.192.1\n")

        # act
        match = CellMgmt._start_gateway_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("111.70.154.150", match.group(1))

    def test_start_dns_regex_should_pass(self):
        # arrange
        SUT = (
            "IP=111.70.154.149\n"
            "SubnetMask=255.255.255.252\n"
            "Gateway=111.70.154.150\n"
            "DNS=168.95.1.1 168.95.192.1\n")

        # act
        match = CellMgmt._start_dns_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("168.95.1.1 168.95.192.1", match.group(1))

    def test_signal_regex_should_pass(self):
        # arrange
        SUT = "umts -41 dbm\n"

        # act
        match = CellMgmt._signal_regex.match(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("-41", match.group(1))


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
