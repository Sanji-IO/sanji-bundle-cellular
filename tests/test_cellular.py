#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
# from mock import mock_open

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

    def setUp(self):
        def zombiefn():
            pass
        self.cellular = Cellular(connection=Mockup())
        self.cellular.get_signal_by_id = zombiefn
        self.cellular.run = zombiefn

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
            self.assertEqual(200, code)
        test_msg["data"] = dict()
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp2, test=True)

        # case 3: data
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
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

        # case 1: data
        def resp1(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"path": "somewhere", "process": "hello_world"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp1, test=True)

        # case 2: data
        def resp2(code=200, data=None):
            self.assertEqual(200, code)
        self.cellular.get_root_by_id(message, response=resp2, test=True)

        # case 3: data
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"enable": "1"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp3, test=True)

        # case 4: data
        def resp4(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"apn": "internet"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp4, test=True)

        # case 5: data
        def resp5(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"username": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp5, test=True)

        # case 6: data
        def resp6(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"name": "root"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp6, test=True)

        # case 7: data
        def resp7(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"dialNumber": "*99#"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp7, test=True)

        # case 8: data
        def resp8(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"password": "*99#"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp8, test=True)

        # case 9: data
        def resp9(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"pinCode": "*99#"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp9, test=True)

        # case 10: data
        def resp10(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"enableAuth": "1"}
        message = Message(test_msg)
        self.cellular.put_root_by_id(message, response=resp10, test=True)

        # case 11: data
        def resp11(code=400, data=None):
            self.assertEqual(400, code)
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
            subprocess.call.return_value = True
            self.cellular.get_signal_by_id('1')

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
            self.cellular.get_status_by_id('1')

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
            self.cellular.set_online_by_id('1')

    def test_set_online_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.set_online_by_id('1')
            self.assertEqual(res, 'fail')

    def test_set_offline_by_id(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.call.return_value = True
            self.cellular.set_offline_by_id('1')

    def test_set_offline_by_id_exception(self):
        self.cellular = Cellular(connection=Mockup())
        with patch("cellular.subprocess") as subprocess:
            subprocess.check_output.side_effect = Exception
            res = self.cellular.set_offline_by_id('1')
            self.assertEqual(res, 'fail')

    def test_init(self):
        with patch("cellular.ModelInitiator") as model:
            model.return_value.db.__getitem__.return_value = 1
            self.cellular.init()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
