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

    @patch("cellular.Cellular.set_pincode_by_id")
    def setUp(self, set_pincode_by_id):
        try:
            os.unlink(dirpath + "/../data/cellular.json")
        except Exception:
            pass
        set_pincode_by_id.return_value = True
        self.cellular = Cellular(connection=Mockup())

    def tearDown(self):
        self.cellular = None

    @patch("cellular.subprocess")
    def put_simple_test_cases(self, subprocess):
        subprocess.check_output.return_value = True
        subprocess.call.return_value = True
        test_msg = {
            "id": 12345,
            "method": "put",
            "param": {"id": "1"},
            "resource": "/network/cellulars"
        }

        # case 1: no data attribute
        def test_put_with_no_data(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=test_put_with_no_data,
                                     test=True)

        # case 2: data dict is empty or no enable exist
        def test_put_with_random_data(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "No such resources."})
        test_msg["data"] = dict()
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_put_with_random_data,
                                     test=True)

        # case 3: data not found
        def test_put_with_unknown_data(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "No such resources."})
        test_msg["data"] = {"path": "abcde"}
        message = Message(test_msg)
        self.cellular.id = 1
        self.cellular.put_root_by_id(message,
                                     response=test_put_with_unknown_data,
                                     test=True)

    def put_complicate_test_cases(self):
        test_msg = {
            "id": 1,
            "method": "put",
            "param": {"id": "1"},
            "resource": "/network/cellulars/1"
        }

        # case 1: data valid. test do not check message coming back
        def test_multi_input_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "internet",
                                                 "username": "whoru",
                                                 "enable": 0,
                                                 "name": "wwan1",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"username": "whoru", "dialNumber": "9999"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_multi_input_with_valid_data,
                                     test=True)

        def test_get_root(code=200, data=None):
            self.assertEqual(200, code)
        self.cellular.get_root_by_id(message,
                                     response=test_get_root,
                                     test=True)

        def test_enable_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "internet",
                                                 "username": "whoru",
                                                 "enable": 1,
                                                 "name": "wwan1",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"enable": 1}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_enable_with_valid_data,
                                     test=True)

        def test_apn_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "whoru",
                                                 "enable": 1,
                                                 "name": "wwan1",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"apn": "hinet"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_apn_with_valid_data,
                                     test=True)

        def test_username_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 1,
                                                 "apn": "hinet",
                                                 "username": "root",
                                                 "enable": 1,
                                                 "name": "wwan1",
                                                 "ip": "",
                                                 "gateway": "",
                                                 "dns": "",
                                                 "dialNumber": "9999",
                                                 "password": "",
                                                 "pinCode": "",
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"username": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_username_with_valid_data,
                                     test=True)

        def test_name_with_valid_data(code=200, data=None):
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
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"name": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_name_with_valid_data,
                                     test=True)

        def test_dialNumber_valid_data(code=200, data=None):
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
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"dialNumber": "*88#"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_dialNumber_valid_data,
                                     test=True)

        def test_password_with_valid_data(code=200, data=None):
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
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"password": "passw0rd"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_password_with_valid_data,
                                     test=True)

        def test_enableAuth_with_valid_data(code=200, data=None):
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
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 1,
                                                 "status": 0,
                                                 "authType": "BOTH",
                                                 "delay": 40
                                                 })
        test_msg["data"] = {"enableAuth": 1, "authType": "BOTH",
                            "username": "root", "password": "passw0rd"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_enableAuth_with_valid_data,
                                     test=True)

        def test_enableAuth_with_no_username(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "require field is empty."})
        test_msg["data"] = {"enableAuth": 1, "username": ""}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_enableAuth_with_no_username,
                                     test=True)

        def test_authType_with_invalid_data(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Data invalid."})
        test_msg["data"] = {"authType": "SSS"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_authType_with_invalid_data,
                                     test=True)

        def test_authType_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"authType": "PAP"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message,
                                     response=test_authType_with_valid_data,
                                     test=True)

    def get_complicate_test_cases(self):
        test_msg = {
            "id": 1,
            "method": "get",
            "param": {"id": "1"},
            "resource": "/network/cellulars"
        }

        def test_get_with_correct_id(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 0,
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
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
            message = Message(test_msg)
            self.cellular.get_root_by_id(message,
                                         response=test_get_with_correct_id,
                                         test=True)

        def test_pincode_with_valid_data(code=200, data=None):
            self.assertEqual(200, code)
            self.assertDictContainsSubset(data, {"id": 0,
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
                                                 "authType": "",
                                                 "modemPort": "/dev/cdc-wdm1",
                                                 "atPort": "/dev/ttyUSB5",
                                                 "enableAuth": 0,
                                                 "status": 0,
                                                 "delay": 40
                                                 })
            test_msg["data"] = {"id": "0", "pinCode": "0000"}
            message = Message(test_msg)
            self.cellular.put_root_by_id(message,
                                         response=test_pincode_with_valid_data,
                                         test=True)

    def get_test_cases(self):
        test_msg = {
            "id": 1,
            "method": "get",
            "resource": "/network/cellulars"
        }

        # case 1: data
        def test_get_root(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(test_msg)
        self.cellular.get_root(message, response=test_get_root, test=True)

    def test_get_signal_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = "-80"
            res = self.cellular.get_signal_by_id('1')
            self.assertEqual(res, "-80")

    def test_get_signal_by_id_fail(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = ""
            res = self.cellular.get_signal_by_id('1')
            self.assertEqual(res, 99)

    def test_get_signal_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.get_signal_by_id('1')
            self.assertEqual(res, 99)

    def test_get_cops_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = "Chung Hwa"
            res = self.cellular.get_cops_by_id('0')
            self.assertEqual(res, "Chung Hwa")

    def test_get_cops_by_id_fail(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = ""
            res = self.cellular.get_cops_by_id('0')
            self.assertEqual(res, "unknown operator")

    def test_get_cops_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.get_cops_by_id('0')
            self.assertEqual(res, "unknown operator")

    def test_get_status_by_id_disconnect(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value =\
                "Connection status: 'disconnected'"
            subprocess.call.return_value = True
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 0)

    def test_get_status_by_id_connect(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value =\
                "Connection status: 'connected'"
            subprocess.call.return_value = True
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 1)

    def test_get_status_by_id_search_fail(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value =\
                "xxxx"
            subprocess.call.return_value = None
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 2)

    def test_get_status_by_id_with_no_cid(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            self.cellular.cid = "1234"
            subprocess.check_output.return_value = True
            subprocess.call.return_value = True
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 2)

    def test_get_status_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.get_status_by_id('1')
            self.assertEqual(res, 2)

    def test_set_online_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0', 'id': '0',
                                   'atPort': '/dev/ttyS0',
                                   'enableAuth': 1, 'apn': 'internet',
                                   'authType': 'PAP',
                                   'username': 'username',
                                   'password': 'password'}]
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.\
                return_value = "\
                                Packet data handle: '123'\
                                CID: '23'"
            self.cellular.cid = "1234"
            res = self.cellular.set_online_by_id('0')
            self.assertEqual(res, True)

    def test_set_online_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.set_online_by_id('1')
            self.assertFalse(res)

    def test_set_offline_by_id_with_no_cid(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = True
            self.cellular.cid = ""
            self.cellular.pdh = ""
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
                                   'modemPort': '/dev/ttyS0',
                                   'atPort': '/dev/ttyS0',
                                   'id': '0', 'apn': 'internet'}]
        self.cellular.get_signal_by_id = Mock(return_value=99)
        self.cellular.is_target_device_appear = Mock(return_value=False)
        self.cellular.get_status_by_id = Mock(return_value=0)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.publish.event = Mock()
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 99)

    def test_reconnect_if_disconnected_operator_fail(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0',
                                   'atPort': '/dev/ttyS0',
                                   'id': '0', 'apn': 'internet'}]
        self.cellular.get_signal_by_id = Mock(return_value=99)
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_status_by_id = Mock(return_value=2)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.publish.event = Mock()
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 99)

    def test_reconnect_if_disconnected_current_offline_setting_offline(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0',
                                   'atPort': '/dev/ttyS0',
                                   'enable': 0,
                                   'id': '0', 'apn': 'internet'}]
        self.cellular.get_signal_by_id = Mock(return_value=99)
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_status_by_id = Mock(return_value=0)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.publish.event = Mock()
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 99)

    def test_reconnect_if_disconnected_when_disconnect_and_enable_true(self):
        self.cellular.model.db = [{'enable': 1,
                                   'modemPort': '/dev/ttyS0',
                                   'atPort': '/dev/ttyS0',
                                   'id': '0', 'apn': 'internet'}]
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_signal_by_id = Mock(return_value=78)
        self.cellular.get_status_by_id = Mock(return_value=0)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.is_leases_file_appear = Mock(return_value=self.filetext)
        self.cellular.set_offline_by_id = Mock()
        self.cellular.set_online_by_id = Mock()
        self.cellular.publish.event = Mock()
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 78)

    def test_reconnect_if_disconnected_when_connect_and_enable_false(self):
        self.cellular.model.db = [{'enable': 0,
                                   'atPort': '/dev/ttyS0',
                                   'modemPort': '/dev/ttyS0', 'id': '0'}]
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_signal_by_id = Mock(return_value=78)
        self.cellular.get_status_by_id = Mock(return_value=1)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.is_leases_file_appear = Mock(return_value=self.filetext)
        self.cellular.publish.event = Mock()
        self.cellular.reconnect_if_disconnected()
        self.assertEqual(self.cellular.model.db[0]['signal'], 78)

    def test_reconnect_if_disconnected_when_disconnect_and_enable_false(self):
        self.cellular.model.db = [{'enable': 1,
                                   'atPort': '/dev/ttyS0',
                                   'modemPort': '/dev/ttyS0', 'id': '0'}]
        self.cellular.is_target_device_appear = Mock(return_value=True)
        self.cellular.get_signal_by_id = Mock(return_value=78)
        self.cellular.get_status_by_id = Mock(return_value=1)
        self.cellular.get_cops_by_id = Mock(return_value="unknown")
        self.cellular.is_leases_file_appear = Mock(return_value=self.filetext)
        self.cellular.publish.event = Mock()
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

    def test_is_leases_file_appear_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
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
            self.cellular.set_pincode_by_id = Mock(return_value=True)
            self.cellular.init()


class TestCellularPinCodeById(unittest.TestCase):

    def setUp(self):
        self.cellular = Cellular(connection=Mockup())

    def tearDown(self):
        self.cellular = None

    def test_set_pincode_by_id(self):
        self.cellular.model.db = [{'pinCode': '0000',
                                   'id': '0',
                                   'atPort': '/dev/ttyS0',
                                   'modemPort': '/dev/ttyS0'}]
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = True
            res = self.cellular.set_pincode_by_id('0', '0000')
            self.assertTrue(res)

    def test_set_pincode_by_id_empty(self):
        self.cellular.model.db = [{'pinCode': '',
                                   'id': '0',
                                   'atPort': '/dev/ttyS0',
                                   'modemPort': '/dev/ttyS0'}]
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.return_value = True
            res = self.cellular.set_pincode_by_id('0', '')
            self.assertTrue(res)

    def test_put_cases(self):
        test_msg = {
            "id": 12345,
            "method": "put",
            "param": {"id": "1"},
            "resource": "/network/cellulars"
        }

        def test_pincode_with_invalid_data(code=400, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "PIN invalid."})
        test_msg["data"] = {"pinCode": "000000"}
        message = Message(test_msg)
        self.cellular.\
            put_root_by_id(message,
                           response=test_pincode_with_invalid_data,
                           test=True)


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
