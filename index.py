#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
from threading import Thread
from traceback import format_exc

from sanji.connection.mqtt import Mqtt
from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator

from voluptuous import All, Any, Length, Match, Range, Required, Schema
from voluptuous import REMOVE_EXTRA

from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError
from cellular_utility.management import Manager
from cellular_utility.vnstat import VnStat, VnStatError

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)

_logger = logging.getLogger("sanji.cellular")


class Index(Sanji):

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("cellular", path_root)

        self._dev_name = None
        self._mgr = None
        self._vnstat = None

        self._init_thread = Thread(
            name="sanji.cellular.init_thread",
            target=self.__initial_procedure)
        self._init_thread.daemon = True
        self._init_thread.start()

    def __initial_procedure(self):
        """
        Continuously check Cellular modem existence.
        Set self._dev_name, self._mgr, self._vnstat properly.
        """
        cell_mgmt = CellMgmt()
        wwan_node = None

        for retry in xrange(0, 4):
            if retry == 3:
                return

            try:
                cell_mgmt.power_on(timeout_sec=60)

                wwan_node = cell_mgmt.m_info().wwan_node

                break

            except CellMgmtError:
                _logger.warning("get wwan_node failure: " + format_exc())
                cell_mgmt.power_off()

        self._dev_name = wwan_node
        self.__create_manager()

        self._vnstat = VnStat(self._dev_name)

    def __create_manager(self):
        pin = self.model.db[0]["pinCode"]
        pin = None if pin == "" else pin

        self._mgr = Manager(
            dev_name=self._dev_name,
            enabled=self.model.db[0]["enable"],
            pin=pin,
            apn=self.model.db[0]["apn"],
            keepalive_enabled=self.model.db[0]["keepalive"]["enable"],
            keepalive_host=self.model.db[0]["keepalive"]["targetHost"],
            keepalive_period_sec=self.model.db[0]["keepalive"]["intervalSec"],
            log_period_sec=60)

        self._mgr.set_update_network_information_callback(
            self._publish_network_info)

        self._mgr.start()

    def __init_completed(self):
        if self._init_thread is None:
            return True

        self._init_thread.join(0)
        if self._init_thread.is_alive():
            return False

        self._init_thread = None
        return True

    @Route(methods="get", resource="/network/cellulars")
    def get_list(self, message, response):
        if not self.__init_completed():
            return response(code=200, data=[])

        if (self._dev_name is None or
                self._mgr is None or
                self._vnstat is None):
            return response(code=200, data=[])

        return response(code=200, data=[self._get()])

    @Route(methods="get", resource="/network/cellulars/:id")
    def get(self, message, response):
        if not self.__init_completed():
            return response(code=400, data={"message": "resource not exist"})

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
        if not self.__init_completed():
            return response(code=400, data={"message": "resource not exist"})

        id_ = int(message.param["id"])
        if id_ != 1:
            return response(code=400, data={"message": "resource not exist"})

        _logger.info(str(message.data))

        data = Index.PUT_SCHEMA(message.data)

        _logger.info(str(data))

        # since all items are required in PUT,
        # its schema is identical to cellular.json
        self.model.db[0] = data
        self.model.save_db()

        if self._mgr is not None:
            self._mgr.stop()
            self._mgr = None

        self.__create_manager()

        return response(code=200, data=self._get())

    def _get(self):
        name = self._dev_name
        if name is None:
            name = "n/a"

        config = self.model.db[0]

        status = self._mgr.status()
        sinfo = self._mgr.static_information()
        cinfo = self._mgr.cellular_information()
        ninfo = self._mgr.network_information()

        try:
            self._vnstat.update()
            usage = self._vnstat.get_usage()

        except VnStatError:
            usage = {
                "txkbyte": "n/a",
                "rxkbyte": "n/a"
            }

        return {
            "id": config["id"],
            "name": name,
            "mode": "n/a" if cinfo is None else cinfo.mode,
            "signal": 0 if cinfo is None else cinfo.signal_dbm,
            "operatorName": "n/a" if cinfo is None else cinfo.operator,
            "iccId": "n/a" if sinfo is None else sinfo.icc_id,
            "imei": "n/a" if sinfo is None else sinfo.imei,
            "pinRetryRemain": "n/a" if sinfo is None else sinfo.pin_retry_remain,

            "status": status.name,
            "ip": "n/a" if ninfo is None else ninfo.ip,
            "netmask": "n/a" if ninfo is None else ninfo.netmask,
            "gateway": "n/a" if ninfo is None else ninfo.gateway,
            "dns": [] if ninfo is None else ninfo.dns_list,
            "usage": {
                "txkbyte": usage["txkbyte"],
                "rxkbyte": usage["rxkbyte"]
            },

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
            nwk_info):

        name = self._dev_name
        if name is None:
            _logger.error("device name not available")
            return

        data = {
            "name": name,
            "ip": nwk_info.ip,
            "netmask": nwk_info.netmask,
            "gateway": nwk_info.gateway,
            "dns": nwk_info.dns_list
        }
        _logger.info("publish network info: " + str(data))
        self.publish.event.put("/network/interface", data=data)


if __name__ == "__main__":
    cellular = Index(connection=Mqtt())
    cellular.start()
