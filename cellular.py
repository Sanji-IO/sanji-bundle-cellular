#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
import subprocess
import re
import sh
from time import sleep
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator
from modemcmd import modemcmd
from modemcmd import ModemcmdTimeoutException
from subprocess import CalledProcessError

from voluptuous import Schema
from voluptuous import Required
from voluptuous import REMOVE_EXTRA
from voluptuous import Range
from voluptuous import All
from voluptuous import Any
from voluptuous import Length

# logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("sanji.cellular")


def save_state(pdh, cid):
    sh.echo("%s,%s" % (pdh, cid), _out="/run/shm/cellular.tmp")


def load_state():
    try:
        return sh.cat("/run/shm/cellular.tmp").split(",")
    except Exception as e:
        _logger.debug(str(e), exc_info=True)
        return ('', '')


class Cellular(Sanji):

    search_router_pattern =\
        re.compile(ur"option routers ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")
    search_dns_pattern =\
        re.compile(ur"option domain-name-server (.*)")
    search_ip_pattern =\
        re.compile(ur"fixed-address ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")
    search_subnet_pattern =\
        re.compile(ur"option subnet-mask ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")
    search_name_pattern =\
        re.compile(ur"interface \"([a-z]+[0-9])\"")
    search_cid_pattern =\
        re.compile(ur"CID: '([0-9]+)'")
    search_pdh_pattern =\
        re.compile(ur"Packet data handle: '([0-9]+)'")
    search_link_pattern =\
        re.compile(ur"Connection status: '([a-z]+)'")
    search_mode_pattern =\
        re.compile(ur"Mode preference: '([a-z]+)'")
    search_band_pattern =\
        re.compile(ur"Band preference: '([a-z]+)'")

    PUT_SCHEMA = Schema({
        Required("id"): int,
        "apn": Any("", All(str, Length(0, 255))),
        "username": Any("", All(str, Length(0, 255))),
        "enable": All(int, Range(min=0, max=1)),
        "dialNumber": All(str, Length(1, 255)),
        "password": Any("", All(str, Length(0, 255))),
        "pinCode": Any("", All(str, Length(0, 255))),
        "enableAuth": All(int, Range(min=0, max=1))
    }, extra=REMOVE_EXTRA)

    def search_name(self):
        name = re.search(self.search_name_pattern, self.dhclient_info)
        if name:
            _logger.debug("name is %s" % name.group(1))
            return name.group(1)

        return "N/A"

    def search_router(self):
        router = re.search(self.search_router_pattern, self.dhclient_info)
        if router:
            _logger.debug("router is %s" % router.group(1))
            return router.group(1)

        return "N/A"

    def search_dns(self):
        dns = re.search(self.search_dns_pattern, self.dhclient_info)
        if dns:
            _logger.debug("dns is %s" % dns.group(1))
            return dns.group(1).split()

        return "N/A"

    def search_ip(self):
        ip = re.search(self.search_ip_pattern, self.dhclient_info)
        if ip:
            _logger.debug("ip is %s" % ip.group(1))
            return ip.group(1)

        return "N/A"

    def search_subnet(self):
        subnet = re.search(self.search_subnet_pattern, self.dhclient_info)
        if subnet:
            _logger.debug("subnet is %s" % subnet.group(1))
            return subnet.group(1)

        return "N/A"

    def is_target_device_appear(self, name):
        return os.path.exists(str(name))

    def reconnect_if_disconnected(self):
        for model in self.model.db:

            if ((self.is_target_device_appear(model["modemPort"]) is False) or
                    (self.is_target_device_appear(model["atPort"]) is False)):
                model["signal"] = 99
                model["status"] = 0
                self.set_signal_led(model["signal"])
                continue

            dev_id = model["id"] - 1
            # update signal
            model["signal"] = self.get_signal_by_id(dev_id)
            model["operatorName"] = self.get_cops_by_id(dev_id)
            model["status"] = self.get_status_by_id(dev_id)
            self.set_signal_led(model["signal"])

            # check network availability
            # if network status down, turn up otherwise disconnect
            _logger.debug(
                "Signal: %s Operator: \"%s\" Status: %s on device path %s"
                % (model["signal"],
                   model["operatorName"],
                   model["status"],
                   model["modemPort"]))

            if self.modifed.get(model["name"], False) is True:
                self.set_offline_by_id(dev_id)
                self.modifed[model["name"]] = False

            # if offline clear previous ip, gateway, etc...
            if model["enable"] == 0 or model["status"] == 0:
                model["router"] = ""
                model["dns"] = ""
                model["ip"] = ""
                model["subnet"] = ""

            if model['status'] == 2:
                continue

            # setting is offline, but current is online = turn offline
            if model["enable"] == 0 and model["status"] == 1:
                self.set_offline_by_id(dev_id)
                continue

            # setting is offline and current is offline = do nothing
            if model["enable"] == 0 and model["status"] == 0:
                continue

            # setting is online and current is offline = start connect
            if model["enable"] == 1 and model["status"] == 0:
                _logger.debug("Start connect")
                self.set_offline_by_id(dev_id)
                self.set_online_by_id(dev_id)

            # update info according to dhclient_info variable
            if self.dhclient_info == "":
                continue

            # parse router
            model["router"] = self.search_router()

            # parse dns
            model["dns"] = self.search_dns()

            # parse ip
            model["ip"] = self.search_ip()

            # parse subnet
            model["subnet"] = self.search_subnet()

            # event notification (in mins)
            count = self.event_counter.get(model["name"], 0)
            if count == 0:
                self.publish.event.put("/network/interface", data={
                    "name": model["name"],
                    "ip": model["ip"],
                    "netmask": model["subnet"],
                    "dns": model["dns"],
                    "gateway": model["router"]
                })

            count = count + 1
            self.event_counter[model["name"]] = 0 if count > 10 else count

            self.model.save_db()

    def _set_signal_led(self, level):
        """
        Attributes:
        level   0: no signal or N/A
                1: marginal
                2: good
                3: excellent
        """
        signals = {
            0: ["0", "0", "0"],
            1: ["0", "0", "1"],
            2: ["0", "1", "1"],
            3: ["1", "1", "1"]
        }
        with open("/sys/class/leds/uc811x:CEL1/brightness", "w") as led1:
            led1.write(signals[level][0])
        with open("/sys/class/leds/uc811x:CEL2/brightness", "w") as led2:
            led2.write(signals[level][1])
        with open("/sys/class/leds/uc811x:CEL3/brightness", "w") as led3:
            led3.write(signals[level][2])

    def set_signal_led(self, signal):
        if signal >= -52 or signal <= -110:
            signal = -120

        if signal >= -73:
            self._set_signal_led(3)
        elif signal >= -93:
            self._set_signal_led(2)
        elif signal >= -109:
            self._set_signal_led(1)
        else:
            self._set_signal_led(0)

    def get_signal_by_id(self, dev_id):
        try:
            tmp = subprocess.check_output(
                "qmicli -p -d %s --nas-get-signal-info | grep RSSI \
                | cut -d \"'\" -f 2 \
                | cut -d \" \" -f 1 \
                | tail -n 1" % (self.model.db[dev_id]["modemPort"]),
                shell=True)
            if len(tmp) > 1:
                return int(str(tmp).strip())
            else:
                return 99
        except Exception as e:
            _logger.debug(e)
            return 99

    def get_cops_by_id(self, dev_id):
        try:
            out = modemcmd(self.model.db[dev_id]["atPort"], "AT+COPS?")
            out = out.split(",")
            if len(out) == 4:
                return out[2].strip("\"")
            _logger.debug(out)
        except ModemcmdTimeoutException as e:
            _logger.debug(e)
        except Exception as e:
            _logger.error(e, exc_info=True)

        return "Unknown Operator"

    def get_status_by_id(self, dev_id):
        try:
            command = ("qmicli -p -d " + self.model.db[dev_id]["modemPort"] +
                       " --wds-get-packet-service-status")
            if len(self.cid) != 0:
                command += (
                    " --client-cid=" + self.cid +
                    " --client-no-release-cid" +
                    " --device-open-net=\"net-802-3|net-no-qos-header\"")

            out = subprocess.check_output(command, shell=True)
            status = re.search(self.search_link_pattern, out)
            if status is None:
                return 2

            if status.group(1) == "connected":
                self.status = 1
            elif status.group(1) == "disconnected":
                self.status = 0

            return self.status
        except Exception:
            self.cid = ""
            self.pdh = ""
            return 2

    def set_online_by_id(self, dev_id):
        try:
            command = "qmicli -p -d " + self.model.db[dev_id]["modemPort"] +\
                      " --wds-start-network=" + self.model.db[dev_id]["apn"] +\
                      " --client-no-release-cid " +\
                      "--device-open-net=\"net-802-3|net-no-qos-header\""

            if self.model.db[dev_id]["enableAuth"] != 0:
                command += "," + self.model.db[dev_id]["authType"] +\
                           "," + self.model.db[dev_id]["username"] +\
                           "," + self.model.db[dev_id]["password"]

            if len(self.cid) != 0:
                command += " --client-cid=" + self.cid

            out = subprocess.check_output(command, shell=True)
            cid = re.search(self.search_cid_pattern, out)
            pdh = re.search(self.search_pdh_pattern, out)
            command = "dhclient -sf " + os.path.abspath(os.path.dirname(__file__)) +\
                      "/hooks/cellular-dhclient-hook " +\
                      self.model.db[dev_id]["name"]
            self.dhclient_info = subprocess.check_output(command, shell=True)
            self.cid = cid.group(1)
            self.pdh = pdh.group(1)
            save_state(self.pdh, self.cid)

            return True
        except Exception as e:
            _logger.debug(e)
            return False

    def set_offline_by_id(self, dev_id):
        self.dhclient_info = ""
        try:
            try:
                subprocess.check_output(
                    ["dhclient", "-r", self.model.db[dev_id]["name"]])
            except CalledProcessError:
                pass
            if len(self.cid) == 0:
                _logger.debug("Network already stopped")
            elif len(self.pdh) == 0:
                _logger.debug("Network already stopped, need to cleanup CID")
                subprocess.check_output(
                    "qmicli -p -d %s --wds-noop --client-cid=%s"
                    % (self.model.db[dev_id]["modemPort"], self.cid),
                    shell=True)
            else:
                _logger.debug("Network stopped success")  #
                subprocess.check_output(
                    "qmicli -p -d %s --wds-stop-network=%s --client-cid=%s"
                    % (self.model.db[dev_id]["modemPort"], self.pdh, self.cid),
                    shell=True)
            try:
                sh.ip("link", "set", self.model.db[dev_id]["name"], "down")
            except:
                pass

            self.pdh = ""
            self.cid = ""
            self.status = ""
            return True
        except Exception as e:
            _logger.debug(str(e), exc_info=True)
            self.pdh = ""
            self.cid = ""
            self.status = ""
            return False

    def set_pincode_by_id(self, dev_id, pinCode):
        pin_len = len(pinCode)
        if pin_len == 0:
            return True
        elif pin_len != 4:
            return False

        try:
            subprocess.check_output(
                "qmicli -p -d %s --dms-uim-verify-pin=PIN,%s"
                % (self.model.db[dev_id]["modemPort"], pinCode), shell=True)
        except Exception, e:
            # if pin code failed, clean up
            self.model.db[dev_id]["pinCode"] = ""
            _logger.debug(e)
            return False

        return True

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.pdh, self.cid = load_state()
        self.status = ""
        self.model = ModelInitiator("cellular", path_root)
        self.event_counter = {}
        self.modifed = {}
        self.dhclient_info = ""

    @Route(methods="get", resource="/network/cellulars")
    def get_root(self, message, response):
        return response(
            data=[obj for obj in self.model.db if obj.get("signal", 99) != 99])

    @Route(methods="get", resource="/network/cellulars/:id")
    def get_root_by_id(self, message, response):
        id = int(message.param["id"]) - 1
        if id > len(self.model.db) or id < 0:
            return response(
                code=400, data={"message": "No such id resources."})
        else:
            return response(code=200, data=self.model.db[id])

    @Route(methods="put", resource="/network/cellulars/:id", schema=PUT_SCHEMA)
    def put_root_by_id(self, message, response):
        if not hasattr(message, "data"):
            return response(code=400, data={"message": "Invalid Input."})

        is_match_param = 0

        id = int(message.param["id"]) - 1
        if id > len(self.model.db) or id < 0:
                return response(
                    code=400, data={"message": "No such id resources."})

        if "enable" in message.data:
            self.model.db[id]["enable"] = message.data["enable"]
            is_match_param = 1

        if "apn" in message.data:
            self.model.db[id]["apn"] = message.data["apn"]
            is_match_param = 1

        if "username" in message.data:
            self.model.db[id]["username"] = message.data["username"]
            is_match_param = 1

        if "name" in message.data:
            self.model.db[id]["name"] = message.data["name"]
            is_match_param = 1

        if "dialNumber" in message.data:
            self.model.db[id]["dialNumber"] = message.data["dialNumber"]
            is_match_param = 1

        if "password" in message.data:
            self.model.db[id]["password"] = message.data["password"]
            is_match_param = 1

        if "pinCode" in message.data:
            res = self.set_pincode_by_id(id, message.data["pinCode"])
            if res is True:
                self.model.db[id]["pinCode"] = message.data["pinCode"]
                is_match_param = 1
            else:
                return response(code=400, data={"message": "PIN invalid."})

        # None / PAP / CHAP / BOTH
        if "authType" in message.data and message.data["authType"] != "None":
            if (message.data["authType"] == "PAP" or
                    message.data["authType"] == "CHAP" or
                    message.data["authType"] == "BOTH"):
                self.model.db[id]["authType"] = message.data["authType"]
                is_match_param = 1
            else:
                return response(code=400, data={"message": "Data invalid."})

        if "enableAuth" in message.data:
            self.model.db[id]["enableAuth"] = message.data["enableAuth"]
            if (message.data["enableAuth"] == 1):
                # authType / username / password MUST ready before enable
                if (len(self.model.db[id]["authType"]) > 0 and
                        len(self.model.db[id]["username"]) > 0 and
                        len(self.model.db[id]["password"]) > 0):
                    is_match_param = 1
                else:
                    return response(code=400, data={"message":
                                    "require field is empty."})

        if is_match_param == 0:
            return response(code=400, data={"message": "No such resources."})
        else:
            self.modifed[self.model.db[id]["name"]] = True

        self.model.save_db()
        return response(code=200, data=self.model.db[id])

    def check_process(self, process, bg=False):
        # /usr/local/libexec/qmi-proxy
        ret = subprocess.call(
            "ps ax | grep \"%s\" | grep -v grep >/dev/null 2>&1" % (process),
            shell=True)
        if ret == 0:
            return
        _logger.debug("%s not exists. starting..." % (process))

        if bg is True:
            process += " &"
        ret = subprocess.call("%s" % (process), shell=True)

        if ret != 0:
            _logger.debug("%s start failed." % (process))

    def check_proxy(self):
        self.check_process("/usr/local/libexec/qmi-proxy", bg=True)

    def run(self):
        self.check_proxy()
        for model in self.model.db:
            if len(model["pinCode"]) > 0:
                self.set_pincode_by_id(model["id"]-1, model["pinCode"])
        while True:
            self.check_proxy()
            self.reconnect_if_disconnected()
            sleep(5)

    def before_stop(self):
        self.model.stop_backup()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.cellular")

    cellular = Cellular(connection=Mqtt())
    cellular.start()
