#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import logging
import unittest

from index import Index

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
            "apn": "internet",
            "pinCode": "0000",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60
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
            "apn": "internet",
            "pinCode": u"0000",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60
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
            "apn": "internet",
            "pinCode": u"",
            "keepalive": {
                "enable": True,
                "targetHost": "8.8.8.8",
                "intervalSec": 60
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
