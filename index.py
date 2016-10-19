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
from voluptuous import REMOVE_EXTRA, Optional, In

from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError
from cellular_utility.management import Manager
from cellular_utility.vnstat import VnStat, VnStatError

from sh import rm, service

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)

_logger = logging.getLogger("sanji.cellular")


class Index(Sanji):

    CONF_SCHEMA = Schema(
        {
            "id": int,
            Required("enable"): bool,
            Required("pdpContext"): {
                Required("static"): bool,
                Required("id"): int,
                Required("retryTimeout"): int,
                Required("primary"): {
                    Required("apn", default="internet"):
                        All(Any(unicode, str), Length(0, 100)),
                    Optional("type", default="ipv4v6"):
                        In(frozenset(["ipv4", "ipv6", "ipv4v6"]))
                },
                Required("secondary", default={}): {
                    Optional("apn"): All(Any(unicode, str), Length(0, 100)),
                    Optional("type", default="ipv4v6"):
                        In(frozenset(["ipv4", "ipv6", "ipv4v6"]))
                }
            },
            Required("pinCode", default=""): Any(Match(r"[0-9]{4,4}"), ""),
            Required("keepalive"): {
                Required("enable"): bool,
                Required("targetHost"): str,
                Required("intervalSec"): All(
                    int,
                    Any(0, Range(min=60, max=86400-1))),
                Required("reboot",
                         default={"enable": False, "cycles": 1}): {
                    Required("enable", default=False): bool,
                    Required("cycles", default=1): All(
                        int,
                        Any(0, Range(min=1, max=48))),
                }
            }
        },
        extra=REMOVE_EXTRA)

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("cellular", path_root)
        self.model.db[0] = Index.CONF_SCHEMA(self.model.db[0])

        self._dev_name = None
        self._mgr = None
        self._vnstat = None

        self._init_thread = Thread(
            name="sanji.cellular.init_thread",
            target=self.__initial_procedure)
        self._init_thread.daemon = True
        self._init_thread.start()
        self.__init_monit_config(
            enable=(self.model.db[0]["enable"] and
                    self.model.db[0]["keepalive"]["enable"] and True and
                    self.model.db[0]["keepalive"]["reboot"]["enable"] and
                    True),
            target_host=self.model.db[0]["keepalive"]["targetHost"],
            cycles=self.model.db[0]["keepalive"]["reboot"]["cycles"]
        )

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
                wwan_node = cell_mgmt.m_info().wwan_node
                break
            except CellMgmtError:
                _logger.warning("get wwan_node failure: " + format_exc())
                cell_mgmt.power_cycle(timeout_sec=60)

        self._dev_name = wwan_node
        self.__create_manager()

        self._vnstat = VnStat(self._dev_name)

    def __create_manager(self):
        pin = self.model.db[0]["pinCode"]
        if "primary" in self.model.db[0]["pdpContext"]:
            pdpc_primary_apn = \
                self.model.db[0]["pdpContext"]["primary"].get(
                    "apn", "internet")
            pdpc_primary_type = \
                self.model.db[0]["pdpContext"]["primary"].get("type", "ipv4v6")
        else:
            pdpc_primary_apn = "internet"
            pdpc_primary_type = "ipv4v6"
        if "secondary" in self.model.db[0]["pdpContext"]:
            pdpc_secondary_apn = \
                self.model.db[0]["pdpContext"]["secondary"].get("apn", "")
            pdpc_secondary_type = \
                self.model.db[0]["pdpContext"]["secondary"].get(
                    "type", "ipv4v6")
        else:
            pdpc_secondary_apn = ""
            pdpc_secondary_type = "ipv4v6"
        pdpc_retry_timeout = self.model.db[0]["pdpContext"]["retryTimeout"]

        self._mgr = Manager(
            dev_name=self._dev_name,
            enabled=self.model.db[0]["enable"],
            pin=None if pin == "" else pin,
            pdp_context_static=self.model.db[0]["pdpContext"]["static"],
            pdp_context_id=self.model.db[0]["pdpContext"]["id"],
            pdp_context_primary_apn=pdpc_primary_apn,
            pdp_context_primary_type=pdpc_primary_type,
            pdp_context_secondary_apn=pdpc_secondary_apn,
            pdp_context_secondary_type=pdpc_secondary_type,
            pdp_context_retry_timeout=pdpc_retry_timeout,
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

    def __init_monit_config(
            self, enable=False, target_host="8.8.8.8", cycles=1):
        if enable is False:
            rm("-rf", "/etc/monit/conf.d/keepalive")
            service("monit", "restart")
            return

        config = """check host targethost with address {target_host}
    if failed icmp type echo
        count 3 with timeout 20 seconds
    then exec "/bin/bash -c '/sbin/cell_mgmt power_off force && /bin/sleep 5 && /sbin/reboot -i -f -d'"
    every {cycles} cycles
"""
        with open("/etc/monit/conf.d/keepalive", "w") as f:
            f.write(config.format(target_host=target_host, cycles=cycles))
        service("monit", "restart")

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

    PUT_SCHEMA = CONF_SCHEMA

    @Route(methods="put", resource="/network/cellulars/:id", schema=PUT_SCHEMA)
    def put(self, message, response):
        if not self.__init_completed():
            return response(code=400, data={"message": "resource not exist"})

        id_ = int(message.param["id"])
        if id_ != 1:
            return response(code=400, data={"message": "resource not exist"})

        _logger.info(str(message.data))

        data = Index.PUT_SCHEMA(message.data)
        data["id"] = id_

        _logger.info(str(data))

        # always use the 1st PDP context for static
        if data["pdpContext"]["static"] is True:
            data["pdpContext"]["id"] = 1

        # since all items are required in PUT,
        # its schema is identical to cellular.json
        self.model.db[0] = data
        self.model.save_db()

        if self._mgr is not None:
            self._mgr.stop()
            self._mgr = None

        self.__create_manager()
        self.__init_monit_config(
            enable=(self.model.db[0]["enable"] and
                    self.model.db[0]["keepalive"]["enable"] and True and
                    self.model.db[0]["keepalive"]["reboot"]["enable"] and
                    True),
            target_host=self.model.db[0]["keepalive"]["targetHost"],
            cycles=self.model.db[0]["keepalive"]["reboot"]["cycles"]
        )

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
            pdpc_list = self._mgr.pdp_context_list()
        except CellMgmtError:
            pdpc_list = []

        try:
            self._vnstat.update()
            usage = self._vnstat.get_usage()

        except VnStatError:
            usage = {
                "txkbyte": -1,
                "rxkbyte": -1
            }

        # clear PIN code if pin error
        if (config["pinCode"] != "" and
                status == Manager.Status.pin):
            config["pinCode"] = ""

            self.model.db[0] = config
            self.model.save_db()

        config["pdpContext"]["list"] = pdpc_list

        return {
            "id": config["id"],
            "name": name,
            "mode": "n/a" if cinfo is None else cinfo.mode,
            "signal": 0 if cinfo is None else cinfo.signal_dbm,
            "operatorName": "n/a" if cinfo is None else cinfo.operator,
            "lac": "n/a" if cinfo is None else cinfo.lac,
            "cellId": "n/a" if cinfo is None else cinfo.cell_id,
            "iccId": "n/a" if sinfo is None else sinfo.icc_id,
            "imei": "n/a" if sinfo is None else sinfo.imei,
            "pinRetryRemain": (
                -1 if sinfo is None else sinfo.pin_retry_remain),

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
            "pdpContext": config["pdpContext"],
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
        self.publish.event.put("/network/interfaces/{}".format(name),
                               data=data)


if __name__ == "__main__":
    cellular = Index(connection=Mqtt())
    cellular.start()
