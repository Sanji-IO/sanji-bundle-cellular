#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from mock import mock_open
from mock import Mock

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from cellular import Cellular
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestCellular(unittest.TestCase):

    filetext = "\
    lease {\n\
      interface \"eth0\";\n\
      fixed-address 192.168.10.26;\n\
      option subnet-mask 255.255.0.0;\n\
      option routers 192.168.31.115;\n\
      option dhcp-lease-time 5566;\n\
      option dhcp-message-type 5;\n\
      option domain-name-servers 8.8.8.58,20.20.20.20,40.40.4.1;\n\
      option dhcp-server-identifier 192.168.31.115;\n\
      option domain-name \"MXcloud115\";\n\
      renew 3 2014/10/29 12:52:19;\n\
      rebind 3 2014/10/29 13:37:52;\n\
      expire 3 2014/10/29 13:49:28;\n\
      }\n\
      "
    filetext_fail = " "

    def setUp(self):
        self.cellular = Cellular(connection=Mockup())

    def tearDown(self):
        self.cellular = None

    @patch("cellular.subprocess")
    def test1_put(self, subprocess):
        subprocess.check_output.return_value = True
        subprocess.call.return_value = True
        test_msg = {
            "id": 12345,
            "method": "put",
            "param": {"id": "1"},
            "resource": "/network/cellulars"
        }

        # case 1: no data attribute
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp1, test=True)

        # case 2: data dict is empty or no enable exist
        def resp2(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "No such resources."})
        test_msg["data"] = dict()
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp2, test=True)

        # case 3: data not found
        def resp3(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "No such resources."})
        test_msg["data"] = {"path": "abcde"}
        message = Message(test_msg)
        self.cellular.id = 1
        self.cellular.put_root_by_id(message, response=resp3, test=True)

    def test2_put(self):
        test_msg = {
            "id": 1,
            "method": "put",
            "param": {"id": "1"},
            "resource": "/network/cellulars"
        }

        # case 1: data valid. test do not check message coming back
        def resp1(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "internet",
                                                 "username": "whoru",
                                                 "enable": 0,
                                                 "name": "ppp",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"username": "whoru", "dialNumber": "9999"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp1, test=True)

        # case 2: data
        def resp2(code=200, data=None):
            self.assertEqual(200, code)
        self.cellular.get_root_by_id(message, response=resp2, test=True)

        # case 3: data
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "internet",
                                                 "username": "whoru",
                                                 "enable": 1,
                                                 "name": "ppp",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"enable": 1}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp3, test=True)

        # case 4: data
        def resp4(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "whoru",
                                                 "enable": 1,
                                                 "name": "ppp",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"apn": "hinet"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp4, test=True)

        # case 5: data
        def resp5(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "ppp",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"username": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp5, test=True)

        # case 6: data
        def resp6(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "root",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"name": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp6, test=True)

        # case 7: data
        def resp7(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "root",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "*88#",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"dialNumber": "*88#"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp7, test=True)

        # case 8: data
        def resp8(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "root",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "*88#",
                                                 "password": "passw0rd",
                                                 "pinCode": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"password": "passw0rd"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp8, test=True)

        # case 9: data
        def resp9(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "root",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "*88#",
                                                 "password": "passw0rd",
                                                 "pinCode": "89191230",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 0,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"pinCode": "89191230"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp9, test=True)

        # case 10: data
        def resp10(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "root",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "*88#",
                                                 "password": "passw0rd",
                                                 "pinCode": "89191230",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "enableAuth": 1,
                                                 "modes": "default",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"enableAuth": 1}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp10, test=True)

        # case 11: data
        def resp11(code=400, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "No such id resources."})
        test_msg["data"] = {"id": "5"}
        message = Message(test_msg)
        self.cellular.model.db = ''
        self.cellular.get_root_by_id(message, response=resp11, test=True)

    def test_get(self):
        test_msg = {
            "id": 1,
            "method": "get",
            "resource": "/network/cellulars"
        }

        # case 1: data
        def resp1(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(test_msg)
        self.cellular.get_root(message, response=resp1, test=True)

    def test_get_signal_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = True
            res = self.cellular.get_signal_by_id('1')
            self.assertEqual(res, 99)

    def test_get_signal_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.get_signal_by_id('1')
            self.assertEqual(res, 99)

    def test_get_status_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.call.return_value = True
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 'disconnected')

    def test_get_status_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 'disconnected')

    def test_set_online_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.call.return_value = True
            res = self.cellular.set_online_by_id('1')
            self.assertEqual(res, True)

    def test_set_online_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.set_online_by_id('1')
            self.assertFalse(res)

    def test_set_offline_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.call.return_value = True
            res = self.cellular.set_offline_by_id('1')
            self.assertEqual(res, True)

    def test_set_offline_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.set_offline_by_id('1')
            self.assertFalse(res)

    def test_search_name(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_name(self.filetext)
        self.assertEqual(res, 'eth0')

    def test_search_name_fail(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_name(self.filetext_fail)
        self.assertEqual(res, 'N/A')

    def test_search_router(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_router(self.filetext)
        self.assertEqual(res, '192.168.31.115')

    def test_search_router_fail(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_router(self.filetext_fail)
        self.assertEqual(res, 'N/A')

    def test_search_dns(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_dns(self.filetext)
        self.assertEqual(res, '8.8.8.58,20.20.20.20,40.40.4.1')

    def test_search_dns_fail(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_dns(self.filetext_fail)
        self.assertEqual(res, 'N/A')

    def test_search_ip(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_ip(self.filetext)
        self.assertEqual(res, '192.168.10.26')

    def test_search_ip_fail(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_ip(self.filetext_fail)
        self.assertEqual(res, 'N/A')

    def test_search_subnet(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_subnet(self.filetext)
        self.assertEqual(res, '255.255.0.0')

    def test_search_subnet_fail(self):
        self.cellular = Cellular(connection=Mockup())
        res = self.cellular.search_subnet(self.filetext_fail)
        self.assertEqual(res, 'N/A')

    def test_reconnect_if_disconnected(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0', 'id': '0'}]
        self.cellular.get_signal_by_id = Mock(return_value=99)
        self.cellular.is_target_device_appear = Mock(return_value=False)
        self.cellular.get_status_by_id = Mock(return_value='disconnected')
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 99)

    def test_reconnect_if_disconnected_when_disconnect_and_enable_true(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0', 'id': '0'}]
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_signal_by_id = Mock(return_value=78)
        self.cellular.get_status_by_id = Mock(return_value="'disconnected'")
        self.cellular.is_leases_file_appear = Mock(return_value=self.filetext)
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 78)

    def test_reconnect_if_disconnected_when_disconnect_and_enable_false(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0', 'id': '0'}]
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_signal_by_id = Mock(return_value=78)
        self.cellular.get_status_by_id = Mock(return_value="'connected'")
        self.cellular.is_leases_file_appear = Mock(return_value=self.filetext)
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 78)

    def test_is_leases_file_appear_true(self):
        m = mock_open()
        with patch("cellular.open", m, create=True):
            res = self.cellular.is_leases_file_appear()
            self.assertEqual(res, '')

    def test_is_leases_file_appear_false(self):
        res = self.cellular.is_leases_file_appear()
        self.assertEqual(res, '')

    def test_is_target_device_appear(self):
        res = self.cellular.is_target_device_appear('data/cellular.json')
        self.assertEqual(res, True)

    def test_is_target_device_appear_false(self):
        res = self.cellular.is_target_device_appear('/dev/asdfasdf')
        self.assertEqual(res, False)

    def test_init(self):
        with patch("cellular.ModelInitiator") as model:
            model.return_value.db.__getitem__.return_value = 1
            self.cellular.init()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
