#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os

from sanji.connection.mqtt import Mqtt
from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator

from voluptuous import All, Any, Length, Match, Range, Required, Schema
from voluptuous import REMOVE_EXTRA

from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError
from cellular_utility.management import Manager


class Index(Sanji):

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("cellular", path_root)

        self._mgr = Manager(self._publish_network_info)
        self._mgr.start()

        self._mgr.set_configuration(
            enabled=self.model.db[0]["enable"],
            apn=self.model.db[0]["apn"],
            pin=self.model.db[0]["pinCode"],
            keepalive_enabled=self.model.db[0]["keepalive"]["enable"],
            keepalive_host=self.model.db[0]["keepalive"]["targetHost"],
            keepalive_period_sec=self.model.db[0]["keepalive"]["intervalSec"])

        self._cell_mgmt = CellMgmt()

        self._name = None

    @Route(methods="get", resource="/network/cellulars")
    def get_list(self, message, response):
        return response(code=200, data=[self._get()])

    @Route(methods="get", resource="/network/cellulars/:id")
    def get(self, message, response):
        id_ = int(message.param["id"])
        if id_ != 1:
            return response(code=400, data={"message": "resource not exist"})

        return response(code=200, data=self._get())

    PUT_SCHEMA = Schema(
        {
            "id": int,
            Required("enable"): bool,
            Required("apn"): All(str, Length(max=100)),
            Required("pinCode", default=""): Any(Match(r"[0-9]{4,4}"), ""),
            Required("keepalive"): {
                Required("enable"): bool,
                Required("targetHost"): str,
                Required("intervalSec"): All(
                    int,
                    Any(0, Range(min=60, max=86400-1)))
            }
        },
        extra=REMOVE_EXTRA)

    @Route(methods="put", resource="/network/cellulars/:id", schema=PUT_SCHEMA)
    def put(self, message, response):
        id_ = int(message.param["id"])
        if id_ != 1:
            return response(code=400, data={"message": "resource not exist"})

        # since all items are required in PUT,
        # its schema is identical to cellular.json
        self.model.db[0] = Index.PUT_SCHEMA(message.data)
        self.model.save_db()

        self._mgr.set_configuration(
            enabled=self.model.db[0]["enable"],
            apn=self.model.db[0]["apn"],
            pin=self.model.db[0]["pinCode"],
            keepalive_enabled=self.model.db[0]["keepalive"]["enable"],
            keepalive_host=self.model.db[0]["keepalive"]["targetHost"],
            keepalive_period_sec=self.model.db[0]["keepalive"]["intervalSec"])

        return response(code=200, data=self._get())

    def _get(self):
        _name = self._get_name()

        config = self.model.db[0]

        cellular_status = self._mgr.cellular_status()
        connection_status = self._mgr.connection_status()

        return {
            "id": config["id"],
            "name": _name,
            "signal": cellular_status["signal"],
            "operatorName": cellular_status["operator"],

            "connected": connection_status["connected"],
            "ip": connection_status["ip"],
            "netmask": connection_status["netmask"],
            "gateway": connection_status["gateway"],
            "dns": connection_status["dns"],

            "enable": config["enable"],
            "apn": config["apn"],
            "pinCode": config["pinCode"],
            "keepalive": {
                "enable": config["keepalive"]["enable"],
                "targetHost": config["keepalive"]["targetHost"],
                "intervalSec": config["keepalive"]["intervalSec"]
            }
        }

    def _publish_network_info(
            self,
            ip,
            netmask,
            gateway,
            dns):

        self.publish.event.put("/network/interface", data={
            "name": self._get_name(),
            "ip": ip,
            "netmask": netmask,
            "gateway": gateway,
            "dns": dns})

    def _get_name(self):
        if self._name is not None:
            return self._name

        try:
            self._name = self._cell_mgmt.m_info()["WWAN_node"]
            return self._name

        except CellMgmtError:
            return "n/a"


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.cellular")

    cellular = Index(connection=Mqtt())
    cellular.start()
