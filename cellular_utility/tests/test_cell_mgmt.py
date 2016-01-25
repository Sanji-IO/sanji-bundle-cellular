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
        SUT = (
            "[/dev/cdc-wdm0] PIN status retrieved successfully\n"
            "[/dev/cdc-wdm0] PIN1:\n"
            "\tStatus: enabled-not-verified\n"
            "\tVerify: 3\n"
            "\tUnblock: 10\n"
            "[/dev/cdc-wdm0] PIN2:\n"
            "\tStatus: blocked\n"
            "\tVerify: 0\n"
            "\tUnblock: 10\n"
        )

        # act
        match = CellMgmt._pin_retry_remain_regex.match(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("3", match.group(1))

    QMICLI_NAS_GET_CELL_LOCATION_INFO_OUTPUT = (
        "[/dev/cdc-wdm0] Successfully got cell location info\n"
        "UMTS Info\n"
        "	Cell ID: '15086'\n"
        "	PLMN: '466'\n"
        "	Location Area Code: '10263'\n"
        "	UTRA Absolute RF Channel Number: '10762'\n"
        "	Primary Scrambling Code: '33'\n"
        "	RSCP: '-109' dBm\n"
        "	ECIO: '-17' dBm\n"
        "	Cell [0]:\n"
        "		UTRA Absolute RF Channel Number: '10762'\n"
        "		Primary Scrambling Code: '335'\n"
        "		RSCP: '-116' dBm\n"
        "		ECIO: '-19' dBm\n"
        "	Cell [1]:\n"
        "		UTRA Absolute RF Channel Number: '10762'\n"
        "		Primary Scrambling Code: '472'\n"
        "		RSCP: '-121' dBm\n"
        "		ECIO: '-24' dBm\n"
        "	Cell [2]:\n"
        "		UTRA Absolute RF Channel Number: '10762'\n"
        "		Primary Scrambling Code: '480'\n"
        "		RSCP: '-121' dBm\n"
        "		ECIO: '-25' dBm\n"
        "	Neighboring GERAN Cell [0]:\n"
        "		GERAN Absolute RF Channel Number: '569'\n"
        "		Network Color Code: '1'\n"
        "		Base Station Color Code: '2'\n"
        "		RSSI: '65438'\n"
        "	Neighboring GERAN Cell [1]:\n"
        "		GERAN Absolute RF Channel Number: '578'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65432'\n"
        "	Neighboring GERAN Cell [2]:\n"
        "		GERAN Absolute RF Channel Number: '589'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65424'\n"
        "	Neighboring GERAN Cell [3]:\n"
        "		GERAN Absolute RF Channel Number: '67'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65424'\n"
        "	Neighboring GERAN Cell [4]:\n"
        "		GERAN Absolute RF Channel Number: '587'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65423'\n"
        "	Neighboring GERAN Cell [5]:\n"
        "		GERAN Absolute RF Channel Number: '584'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65423'\n"
        "	Neighboring GERAN Cell [6]:\n"
        "		GERAN Absolute RF Channel Number: '595'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65422'\n"
        "	Neighboring GERAN Cell [7]:\n"
        "		GERAN Absolute RF Channel Number: '73'\n"
        "		Network Color Code: 'unavailable'\n"
        "		Base Station Color Code: 'unavailable'\n"
        "		RSSI: '65422'\n"
        "UMTS Cell ID: '17251054'\n"
        "UMTS Info Neighboring LTE\n"
        "	RRC State: 'disconnected'\n"
        "	Frequency [0]:\n"
        "		EUTRA Absolute RF Channel Number: '1725'\n"
        "		Physical Cell ID: '388'\n"
        "		RSRP: '-126.000000' dBm\n"
        "		RSRQ: '-14.000000' dB\n"
        "		Cell Selection RX Level: '-6'\n"
        "		Is TDD?: 'no'\n"
        "	Frequency [1]:\n"
        "		EUTRA Absolute RF Channel Number: '3650'\n"
        "		Physical Cell ID: '166'\n"
        "		RSRP: '-128.000000' dBm\n"
        "		RSRQ: '-14.000000' dB\n"
        "		Cell Selection RX Level: '-8'\n"
        "		Is TDD?: 'no'\n")

    def test_cellular_location_cell_id_regex_should_pass(self):
        # arrange
        SUT = TestCellMgmt.QMICLI_NAS_GET_CELL_LOCATION_INFO_OUTPUT

        # act
        match = CellMgmt._cellular_location_cell_id_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("15086", match.group(1))

    def test_cellular_location_lac_regex_should_pass(self):
        # arrange
        SUT = TestCellMgmt.QMICLI_NAS_GET_CELL_LOCATION_INFO_OUTPUT

        # act
        match = CellMgmt._cellular_location_lac_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("10263", match.group(1))

    def test_cellular_location_cell_id_regex_with_unavailable_should_pass(self):
        # arrange
        SUT = (
            "[/dev/cdc-wdm0] Successfully got cell location info\n"
            "UMTS Info\n"
            "    Cell ID: 'unavailable'\n"
            "    PLMN: '466'\n"
            "    Location Area Code: '10233'\n"
            "    UTRA Absolute RF Channel Number: '10762'\n"
            "    Primary Scrambling Code: '335'\n"
            "    RSCP: '-81' dBm\n"
            "    ECIO: '-11' dBm\n"
            "    Cell [0]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '33'\n"
            "        RSCP: '-89' dBm\n"
            "        ECIO: '-17' dBm\n"
            "    Cell [1]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '365'\n"
            "        RSCP: '-90' dBm\n"
            "        ECIO: '-18' dBm\n"
            "    Cell [2]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '223'\n"
            "        RSCP: '-92' dBm\n"
            "        ECIO: '-20' dBm\n"
            "    Cell [3]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '343'\n"
            "        RSCP: '-92' dBm\n"
            "        ECIO: '-20' dBm\n"
            "    Cell [4]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '480'\n"
            "        RSCP: '-94' dBm\n"
            "        ECIO: '-21' dBm\n"
            "    Cell [5]:\n"
            "        UTRA Absolute RF Channel Number: '10787'\n"
            "        Primary Scrambling Code: '207'\n"
            "        RSCP: '-94' dBm\n"
            "        ECIO: '-22' dBm\n"
            "UMTS Cell ID: '4294967295'\n"
            "UMTS Info Neighboring LTE\n"
            "    RRC State: 'cell-dch'\n")

        # act
        match = CellMgmt._cellular_location_cell_id_regex.search(SUT)

        # assert
        self.assertTrue(match)
        self.assertEqual("unavailable", match.group(1))


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
