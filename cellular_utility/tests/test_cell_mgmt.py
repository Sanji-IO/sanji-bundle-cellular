#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import logging
import unittest
from mock import patch, Mock


def mock_retrying(f):
    def wrapped_f():
        return f()
    return wrapped_f


try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    patch('cellular_utility.cell_mgmt.retrying', lambda x: x).start()
    from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestCellMgmt(unittest.TestCase):
    @patch("cellular_utility.cell_mgmt.sh")
    def setUp(self, mock_sh):
        self.cell_mgmt = CellMgmt()

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
        self.assertEqual("umts", match.group(1))
        self.assertEqual("-41", match.group(2))

    def test_m_info_regex_should_pass(self):
        # arrange
        SUT = (
            "Module=MC7304\n"
            "WWAN_node=wwan0\n"
            "AT_port=/dev/ttyUSB2\n"
            "GPS_port=/dev/ttyUSB1\n"
            "LAC=2817\n"
            "CellID=01073AEE\n"
            "ICC-ID=1234567890123456\n"
            "IMEI=0123456789012345\n"
            "QMI_port=/dev/cdc-wdm0\n")

        # act
        match = CellMgmt._m_info_regex.match(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("MC7304", match.group(1))
        self.assertEqual("wwan0", match.group(2))
        self.assertEqual("2817", match.group(3))
        self.assertEqual("01073AEE", match.group(4))
        self.assertEqual("1234567890123456", match.group(5))
        self.assertEqual("0123456789012345", match.group(6))
        self.assertEqual("/dev/cdc-wdm0", match.group(7))

    def test_operator_regex_should_pass(self):
        # arrange
        SUT = "Chunghwa Telecom\n"

        # act
        match = CellMgmt._operator_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_sim_status_ready_regex_should_pass(self):
        # arrange
        SUT = "+CPIN: READY\n"

        # act
        match = CellMgmt._sim_status_ready_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_sim_status_sim_pin_regex_should_pass(self):
        # arrange
        SUT = "+CPIN: SIM PIN\n"

        # act
        match = CellMgmt._sim_status_sim_pin_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_pin_retry_remain_regex_should_pass(self):
        # arrange
        SUT = ("[/dev/cdc-wdm1] Successfully got card status\n"
               "Provisioning applications:\n"
               "\tPrimary GW:   slot '0', application '0'\n"
               "\tPrimary 1X:   session doesn't exist\n"
               "\tSecondary GW: session doesn't exist\n"
               "\tSecondary 1X: session doesn't exist\n"
               "Card [0]:\n"
               "\tCard state: 'present'\n"
               "\tUPIN state: 'not-initialized'\n"
               "\t\tUPIN retries: '0'\n"
               "\t\tUPUK retries: '0'\n"
               "\tApplication [0]:\n"
               "\t\tApplication type:  'usim (2)'\n"
               "\t\tApplication state: 'ready'\n"
               "\t\tApplication ID:\n"
               "\t\t\tA0:00:00:00:87:10:02:FF:33:FF:01:89:06:05:00:FF\n"
               "\t\tPersonalization state: 'ready'\n"
               "\t\tUPIN replaces PIN1: 'no'\n"
               "\t\tPIN1 state: 'enabled-verified'\n"
               "\t\t\tPIN1 retries: '3'\n"
               "\t\t\tPUK1 retries: '10'\n"
               "\t\tPIN2 state: 'blocked'\n"
               "\t\t\tPIN2 retries: '0'\n"
               "\t\t\tPUK2 retries: '10'\n")

        # act
        match = CellMgmt._pin_retry_remain_regex.match(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("3", match.group(2))

    def test_at_response_ok_regex_should_pass(self):
        # arrange
        SUT = "\n\nOK\n\n"

        # act
        match = CellMgmt._at_response_ok_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_at_response_err_regex_should_pass(self):
        # arrange
        SUT = "\n\nERROR\n\n"

        # act
        match = CellMgmt._at_response_err_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_at_response_cme_err_regex_should_pass(self):
        # arrange
        SUT = "\n\n+CME ERROR: Unknown error\n\n"

        # act
        match = CellMgmt._at_response_cme_err_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_at_sysinfo_attached_regex_should_pass(self):
        # arrange
        SUT = "^SYSINFO: 2,3,0,5,1"

        # act
        match = CellMgmt._at_sysinfo_attached_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_at_cgdcont_regex_should_pass(self):
        # arrange
        SUT = (
            "+CGDCONT: 1,\"IPV4V6\",\"internet\","
            "\"0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0\",0,0,0,0")

        # act
        match = CellMgmt._at_cgdcont_regex.match(SUT)

        # assert
        self.assertTrue(match)

    def test_at_with_response_ok(self):
        # arrange
        SUT = "\n\nOK\n\n"

        # act
        self.cell_mgmt._cell_mgmt = Mock(return_value=SUT)
        res = self.cell_mgmt.at("at")

        # assert
        self.assertEqual("ok", res["status"])

    def test_at_with_response_ok_and_data(self):
        # arrange
        SUT = "\n\n+CFUN: 1\n\nOK\n\n"

        # act
        self.cell_mgmt._cell_mgmt = Mock(return_value=SUT)
        res = self.cell_mgmt.at("at")

        # assert
        self.assertEqual("ok", res["status"])
        self.assertEqual("+CFUN: 1", res["info"])

    def test_at_with_response_cme_err(self):
        # arrange
        SUT = "\n\n+CME ERROR: Unknown error\n\n"

        # act
        self.cell_mgmt._cell_mgmt = Mock(return_value=SUT)
        res = self.cell_mgmt.at("at")

        # assert
        self.assertEqual("cme-err", res["status"])
        self.assertEqual("Unknown error", res["info"])

    def test_at_with_response_err(self):
        # arrange
        SUT = "\n\nERROR\n\n"

        # act
        self.cell_mgmt._cell_mgmt = Mock(return_value=SUT)
        res = self.cell_mgmt.at("at")

        # assert
        self.assertEqual("err", res["status"])

    def test_at_with_unexpected_output_should_raise_fail(self):
        # arrange
        SUT = "\n\nERR\n\n"

        # act
        self.cell_mgmt._cell_mgmt = Mock(return_value=SUT)

        # assert
        with self.assertRaises(CellMgmtError):
            self.cell_mgmt.at("at")


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
