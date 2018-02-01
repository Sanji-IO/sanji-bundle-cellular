#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from index import Index
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    print (e)
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestCellularStatic(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_put_schema_should_pass(self):
        # arrange
        SUT = {
            "enable": True,
            "pdpContext": {
                "static": True,
                "id": 1,
                "retryTimeout": 1200,
                "primary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                },
                "secondary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                }
            },
            "pinCode": "0000",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60,
                "reboot": {
                    "enable": False,
                    "cycles": 1
                }
            }
        }

        # act
        data = Index.PUT_SCHEMA(SUT)

        # assert
        self.assertEqual(SUT, data)

    def test_put_schema_with_id_should_pass(self):
        # arrange
        SUT = {
            "id": 0,
            "enable": True,
            "pdpContext": {
                "static": True,
                "id": 1,
                "retryTimeout": 1200,
                "primary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                },
                "secondary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                }
            },
            "pinCode": u"0000",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60,
                "reboot": {
                    "enable": False,
                    "cycles": 1
                }
            }
        }

        # act
        data = Index.PUT_SCHEMA(SUT)

        # assert
        self.assertEqual(SUT, data)

    def test_put_schema_with_empty_pin_code_should_pass(self):
        # arrange
        SUT = {
            "id": 1,
            "enable": True,
            "pdpContext": {
                "static": True,
                "id": 1,
                "retryTimeout": 1200,
                "primary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                },
                "secondary": {
                    "apn": "internet",
                    "type": "ipv4v6",
                    "auth": {
                        "protocol": "none"
                    }
                }
            },
            "pinCode": u"",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60,
                "reboot": {
                    "enable": False,
                    "cycles": 1
                }
            }
        }

        # act
        data = Index.PUT_SCHEMA(SUT)

        # assert
        self.assertEqual(SUT, data)


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Cellular Test")
    unittest.main()
