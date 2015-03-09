#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
import subprocess
import re
from time import sleep
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator


logger = logging.getLogger()


class Cellular(Sanji):
    search_router_pattern =\
        re.compile(ur'option routers ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)')
    search_dns_pattern =\
        re.compile(ur'option domain-name-servers (.*);')
    search_ip_pattern =\
        re.compile(ur'fixed-address ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)')
    search_subnet_pattern =\
        re.compile(ur'option subnet-mask ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)')
    search_name_pattern =\
        re.compile(ur'interface "([a-z]+[0-9])"')
    search_cid_pattern =\
        re.compile(ur'CID: \'([0-9]+)\'')
    search_pdh_pattern =\
        re.compile(ur'Packet data handle: \'([0-9]+)\'')
    search_link_pattern =\
        re.compile(ur'Connection status: \'([a-z]+)\'')
    search_mode_pattern =\
        re.compile(ur'Mode preference: \'([a-z]+)\'')
    search_band_pattern =\
        re.compile(ur'Band preference: \'([a-z]+)\'')

    def search_name(self, filetext):
        name = re.search(self.search_name_pattern, filetext)
        if name:
            logger.debug("name is %s" % name.group(1))
            return name.group(1)

        return 'N/A'

    def search_router(self, filetext):
        router = re.search(self.search_router_pattern, filetext)
        if router:
            logger.debug("router is %s" % router.group(1))
            return router.group(1)

        return 'N/A'

    def search_dns(self, filetext):
        dns = re.search(self.search_dns_pattern, filetext)
        if dns:
            logger.debug("dns is %s" % dns.group(1))
            return dns.group(1)

        return 'N/A'

    def search_ip(self, filetext):
        ip = re.search(self.search_ip_pattern, filetext)
        if ip:
            logger.debug("ip is %s" % ip.group(1))
            return ip.group(1)

        return 'N/A'

    def search_subnet(self, filetext):
        subnet = re.search(self.search_subnet_pattern, filetext)
        if subnet:
            logger.debug("subnet is %s" % subnet.group(1))
            return subnet.group(1)

        return 'N/A'

    def is_target_device_appear(self, name):
        return os.path.exists(str(name))

    def is_leases_file_appear(self):
        try:
            with open('/var/lib/dhcp/dhclient.leases', 'r') as leases:
                filetext = leases.read()
                return filetext
        except Exception:
            logger.debug("File open failure")
            return ''

    def reconnect_if_disconnected(self):
        for model in self.model.db:

            if ((self.is_target_device_appear(model['modemPort']) is False) or
                    (self.is_target_device_appear(model['atPort']) is False)):
                model['signal'] = 99
                model['status'] = 0
                continue

            dev_id = model['id'] - 1
            # update signal
            model['signal'] = self.get_signal_by_id(dev_id)
            model['operatorName'] = self.get_cops_by_id(dev_id)
            model['status'] = self.get_status_by_id(dev_id)

            # check network availability
            # if network status down, turn up otherwise disconnect
            logger.debug(
                "Signal: %s Operator: \"%s\" Status: %s on device path %s"
                % (model['signal'],
                   model['operatorName'],
                   model['status'],
                   model['modemPort']))

            if model['status'] == 2:
                continue

            # setting is offline, but current is online = turn offline
            if model['enable'] == 0 and model['status'] == 1:
                self.set_offline_by_id(dev_id)
                continue

            # setting is online and current is online = do nothing
            if model['enable'] == 1 and model['status'] == 1:
                continue

            # setting is offline and current is offline = do nothing
            if model['enable'] == 0 and model['status'] == 0:
                continue

            # setting is online and current is offline = start connect
            logger.debug("Start connect")
            self.set_offline_by_id(dev_id)
            self.set_online_by_id(dev_id)

            # update info according to dhclient.leases
            filetext = self.is_leases_file_appear()
            if filetext == '':
                continue

            # parse name
            model['name'] = self.search_name(filetext)

            # parse router
            model['router'] = self.search_router(filetext)

            # parse dns
            model['dns'] = self.search_dns(filetext)

            # parse ip
            model['ip'] = self.search_ip(filetext)

            # parse subnet
            model['subnet'] = self.search_subnet(filetext)

            # event notification
            self.publish.event.put(
                "/notify/cellular/online/%s" % model['id'], data=model)

            self.model.save_db()

    def get_signal_by_id(self, dev_id):
        try:
            tmp = subprocess.check_output(
                "qmicli -p -d %s --nas-get-signal-info | grep RSSI \
                | cut -d \"'\" -f 2 \
                | cut -d \" \" -f 1 \
                | tail -n 1" % (self.model.db[dev_id]['modemPort']),
                shell=True)
            if len(tmp) > 1:
                return str(tmp).strip()
            else:
                return 99
        except Exception as e:
            logger.debug(e)
            return 99

    def get_cops_by_id(self, dev_id):
        try:
            command = "modem-cmd " + self.model.db[dev_id]['atPort'] +\
                      " \"AT+COPS?\"" + " |awk -F ',' '{print $3}'|tr -d '\"'"
            tmp = subprocess.check_output(command, shell=True)
            if len(tmp) > 1:
                return tmp.strip()
            else:
                return 'unknown operator'
        except Exception as e:
            logger.debug(e)
            return 'unknown operator'

    def get_status_by_id(self, dev_id):
        try:
            command = ("qmicli -p -d " + self.model.db[dev_id]['modemPort'] +
                       " --wds-get-packet-service-status")
            if len(self.cid) != 0:
                command += (" --client-cid=" + self.cid +
                            " --client-no-release-cid")

            out = subprocess.check_output(command, shell=True)
            status = re.search(self.search_link_pattern, out)
            if status is None:
                return 2

            if status.group(1) == 'connected':
                self.status = 1
            elif status.group(1) == 'disconnected':
                self.status = 0

            return self.status
        except Exception:
            self.cid = ''
            self.pdh = ''
            return 2

    def set_online_by_id(self, dev_id):
        try:
            subprocess.check_output("rm -rf /var/lib/dhcp/dhclient.leases",
                                    shell=True)
            command = "qmicli -p -d " + self.model.db[dev_id]['modemPort'] +\
                      " --wds-start-network=" + self.model.db[dev_id]['apn'] +\
                      " --client-no-release-cid"

            if self.model.db[dev_id]['enableAuth'] != 0:
                command += "," + self.model.db[dev_id]['authType'] +\
                           "," + self.model.db[dev_id]['username'] +\
                           "," + self.model.db[dev_id]['password']

            if len(self.cid) != 0:
                command += " --client-cid=" + self.cid

            out = subprocess.check_output(command, shell=True)
            cid = re.search(self.search_cid_pattern, out)
            pdh = re.search(self.search_pdh_pattern, out)
            self.check_dhclient(self.model.db[dev_id]['name'])
            self.cid = cid.group(1)
            self.pdh = pdh.group(1)

            return True
        except Exception as e:
            logger.debug(e)
            return False

    def set_offline_by_id(self, dev_id):
        try:
            subprocess.check_output(
                ["dhclient", "-r", self.model.db[dev_id]['name']])
            if len(self.cid) == 0:
                logger.debug("Network already stopped")
            elif len(self.pdh) == 0:
                logger.debug("Network already stopped, need to cleanup CID")
                subprocess.check_output(
                    "qmicli -p -d %s --wds-noop --client-cid=%s"
                    % (self.model.db[dev_id]['modemPort'], self.cid),
                    shell=True)
            else:
                logger.debug("Network stopped success")  #
                subprocess.check_output(
                    "qmicli -p -d %s --wds-stop-network=%s --client-cid=%s"
                    % (self.model.db[dev_id]['modemPort'], self.pdh, self.cid),
                    shell=True)
            self.pdh = ''
            self.cid = ''
            self.status = ''
            return True
        except Exception:
            self.pdh = ''
            self.cid = ''
            self.status = ''
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
                % (self.model.db[dev_id]['modemPort'], pinCode), shell=True)
        except Exception, e:
            # if pin code failed, clean up
            self.model.db[dev_id]['pinCode'] = ""
            logger.debug(e)
            return False

        return True

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.cid = ''
        self.pdh = ''
        self.status = ''
        self.model = ModelInitiator("cellular", path_root)

    @Route(methods="get", resource="/network/cellulars")
    def get_root(self, message, response):
        return response(data=self.model.db)

    @Route(methods="get", resource="/network/cellulars/:id")
    def get_root_by_id(self, message, response):
        id = int(message.param['id']) - 1
        if id > len(self.model.db) or id < 0:
            return response(
                code=400, data={"message": "No such id resources."})
        else:
            return response(code=200, data=self.model.db[id])

    @Route(methods="put", resource="/network/cellulars/:id")
    def put_root_by_id(self, message, response):
        if not hasattr(message, "data"):
            return response(code=400, data={"message": "Invalid Input."})

        is_match_param = 0

        id = int(message.param['id']) - 1
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
        if "authType" in message.data:
            if (message.data["authType"] == "PAP" or
                    message.data["authType"] == "CHAP" or
                    message.data["authType"] == "BOTH"):
                self.model.db[id]["authType"] = message.data["authType"]
                is_match_param = 1
            else:
                return response(code=400, data={"message": "Data invalid."})

        if "enableAuth" in message.data:
            if (message.data["enableAuth"] == 1):
                # authType / username / password MUST ready before enable
                if (len(self.model.db[id]["authType"]) > 0 and
                        len(self.model.db[id]["username"]) > 0 and
                        len(self.model.db[id]["password"]) > 0):
                    self.model.db[id]["enableAuth"] =\
                        message.data["enableAuth"]
                    is_match_param = 1
                else:
                    return response(code=400, data={"message":
                                    "require field is empty."})

        if is_match_param == 0:
            return response(code=400, data={"message": "No such resources."})

        self.model.save_db()
        return response(code=200, data=self.model.db[id])

    def check_process(self, process, bg=False):
        # /usr/local/libexec/qmi-proxy
        ret = subprocess.call(
            "ps ax | grep \"%s\" | grep -v grep >/dev/null 2>&1" % (process),
            shell=True)
        if ret == 0:
            return
        logger.debug("%s not exists. starting..." % (process))

        if bg is True:
            process += " &"
        ret = subprocess.call("%s" % (process), shell=True)

        if ret != 0:
            logger.debug("%s start failed." % (process))

    def check_proxy(self):
        self.check_process("/usr/local/libexec/qmi-proxy", bg=True)

    def check_dhclient(self, interface):
        self.check_process("dhclient %s" % (interface))

    def run(self):
        self.check_proxy()
        for model in self.model.db:
            if len(model["pinCode"]) == 4:
                self.set_pincode_by_id(model['id'], model["pinCode"])
        while True:
            self.check_proxy()
            self.reconnect_if_disconnected()
            sleep(5)

    def before_stop(self):
        self.model.stop_backup()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Sanji Cellular")

    cellular = Cellular(connection=Mqtt())
    cellular.start()
