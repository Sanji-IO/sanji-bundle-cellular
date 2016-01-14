"""
Helper library.
"""

import logging
import sys

from enum import Enum
from monotonic import monotonic
from subprocess import check_call, CalledProcessError
from threading import Thread
from time import sleep
from traceback import format_exc, print_exc

from cellular_utility.cell_mgmt import (
    CellMgmt, CellMgmtError, SimStatus, Signal)
from cellular_utility.event import Log

_logger = logging.getLogger("sanji.cellular")


class CellularInformation(object):
    def __init__(
            self,
            sim_status,
            mode=None,
            signal=None,
            operator=None,
            lac=None,
            cell_id=None,
            icc_id=None,
            imei=None,
            pin_retry_remain=None):
        self._sim_status = sim_status

        self._mode = "" if mode is None else mode
        self._signal = 0 if signal is None else signal
        self._operator = "" if operator is None else operator
        self._lac = "" if lac is None else lac
        self._cell_id = "" if cell_id is None else cell_id
        self._icc_id = "" if icc_id is None else icc_id
        self._imei = "" if imei is None else imei
        self._pin_retry_remain = (
            -1 if pin_retry_remain is None else pin_retry_remain
        )

    @property
    def sim_status(self):
        return self._sim_status

    @property
    def mode(self):
        return self._mode

    @property
    def signal(self):
        return self._signal

    @property
    def operator(self):
        return self._operator

    @property
    def lac(self):
        return self._lac

    @property
    def cell_id(self):
        return self._cell_id

    @property
    def icc_id(self):
        return self._icc_id

    @property
    def imei(self):
        return self._imei

    @property
    def pin_retry_remain(self):
        return self._pin_retry_remain


class CellularObserver(object):

    CHECK_PERIOD_SEC = 30

    def __init__(
            self):
        self._stop = False
        self._cell_mgmt = CellMgmt()
        self._thread = None

    def start(
            self,
            update_cellular_information):
        def main_thread():
            next_check = monotonic()
            while not self._stop:

                now = monotonic()
                if now < next_check:
                    sleep(1)
                    continue

                next_check = now + CellularObserver.CHECK_PERIOD_SEC

                cellular_information = self._get_cellular_information()
                update_cellular_information(cellular_information)

        self._stop = False
        self._thread = Thread(target=main_thread)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()

    def _get_cellular_information(self):
        try:
            if self._cell_mgmt.sim_status() == SimStatus.nosim:
                return CellularInformation(sim_status="nosim")

            sim_status = self._cell_mgmt.sim_status()

            try:
                signal = self._cell_mgmt.signal()
            except CellMgmtError:
                _logger.warning(format_exc())
                signal = Signal()

            operator = self._cell_mgmt.operator()

            m_info = self._cell_mgmt.m_info()

            try:
                pin_retry_remain = self._cell_mgmt.get_pin_retry_remain()
            except CellMgmtError:
                _logger.warning(format_exc())
                pin_retry_remain = -1

            return CellularInformation(
                sim_status.name,
                signal.mode,
                signal.rssi_dbm,
                operator,
                m_info.lac,
                m_info.cell_id,
                m_info.icc_id,
                m_info.imei,
                pin_retry_remain)

        except CellMgmtError:
            _logger.warning(format_exc())
            return None


class NetworkInformation(object):
    def __init__(
            self,
            ip,
            netmask,
            gateway,
            dns_list):
        self._ip = ip
        self._netmask = netmask
        self._gateway = gateway
        self._dns_list = dns_list

    @property
    def ip(self):
        return self._ip

    @property
    def netmask(self):
        return self._netmask

    @property
    def gateway(self):
        return self._gateway

    @property
    def dns_list(self):
        return self._dns_list


class CellularConnector(object):
    """
    Tries Cellular connection continuously.
    """

    PING_REQUEST_COUNT = 3
    PING_TIMEOUT_SEC = 20

    class State(Enum):
        connecting = 0
        connected = 1
        connect_failed = 2
        idle = 3

    def __init__(
            self,
            dev_name,
            apn,
            pin,
            check_period_sec,
            log,
            keepalive_host=None):

        self._dev_name = dev_name
        self._apn = apn
        self._pin = pin
        self._check_period_sec = check_period_sec
        self._keepalive_host = keepalive_host
        self._log = log

        self._cell_mgmt = CellMgmt()

        self._connect_thread = None
        self._stop = False

        self._state = CellularConnector.State.idle

    def state(self):
        """Return an instance of CellularConnector.State."""
        return self._state

    def start(self, update_network_information):
        """
        Start Cellular connection.

        update_network_information should be a callable like:
            update_network_information(NetworkInformation)
        """

        def main_thread():
            """
            Try to connect.
            If connect fails for 3 times, power-cycle Cellular module and
              continue trying.
            """

            while not self._stop:
                try:
                    network_information = None

                    # connect Cellular
                    for _ in range(0, 4):
                        if self._stop:
                            break

                        network_information = None
                        update_network_information(network_information)

                        self._state = CellularConnector.State.connecting
                        network_information = self._reconnect()
                        if network_information is None:
                            self._state = \
                                CellularConnector.State.connect_failed
                            # retry in 10 seconds
                            sleep(10)
                            continue

                        update_network_information(network_information)
                        self._state = CellularConnector.State.connected

                        # sleep awhile to let ip-route take effect
                        sleep(10)
                        break

                    if self._stop:
                        break

                    # retry count exceeded, power-cycle cellular module
                    if network_information is None:
                        self._power_cycle()
                        continue

                    # cellular connected, start check-alive
                    self._check_alive()

                except CellMgmtError:
                    print_exc()
                    continue

            self._cell_mgmt.stop()
            self._log.log_event_cellular_disconnect()
            update_network_information(None)
            self._state = CellularConnector.State.idle

        self._stop = False
        self._connect_thread = Thread(target=main_thread)
        self._connect_thread.daemon = True
        self._connect_thread.start()

    def stop(self):
        """
        Stop Cellular connection.
        """
        self._stop = True
        self._connect_thread.join()

    def _reconnect(self):
        """
        Returns NetworkInformation if connected, otherwise None.
        """

        self._log.log_event_connect_begin()

        sim_status = self._cell_mgmt.sim_status()
        _logger.debug(
            "sim_status = {}, self._pin = {}".format(
                sim_status.name,
                self._pin
            )
        )

        if sim_status == SimStatus.nosim:
            self._log.log_event_nosim()
            _logger.debug("reconnect: abort: sim-status: " + sim_status.name)
            return None

        elif sim_status == SimStatus.pin:
            if self._pin == "":
                _logger.warning("no pin provided")
                self._log.log_event_pin_error("")
                return None

            try:
                _logger.debug("trying pin: {}".format(self._pin))
                self._cell_mgmt.set_pin(self._pin)

            except CellMgmtError:
                _logger.warning(format_exc())
                self._log.log_event_pin_error(self._pin)

                # this PIN should not be used anymore
                self._stop = True
                return None

        self._cell_mgmt.stop()

        try:
            network_info = self._cell_mgmt.start(
                apn=self._apn)

        except CellMgmtError:
            self._log.log_event_connect_failure()

            print_exc()

            return None

        if not self._cell_mgmt.status():
            self._log.log_event_connect_failure()

            return None

        # publish cellular information here
        network_information = NetworkInformation(
            network_info["ip"],
            network_info["netmask"],
            network_info["gateway"],
            network_info["dns"])

        self._log.log_event_connect_success(
            network_information)

        return network_information

    def _ping(self):
        """
        Return whether ping succeeded.
        """
        if not self._keepalive_host:
            return True

        for _ in xrange(0, self.PING_REQUEST_COUNT):
            cmd = [
                "ping",
                "-c", "1",
                "-I", self._dev_name,
                "-W", str(self.PING_TIMEOUT_SEC),
                self._keepalive_host]

            _logger.debug("cmd = " + repr(cmd))

            try:
                check_call(cmd)
                return True

            except CalledProcessError:
                continue

        return False

    def _power_cycle(self):
        """
        As title.
        """
        _logger.warning("power-cycle cellular module")

        self._log.log_event_power_cycle()

        self._cell_mgmt.stop()
        self._cell_mgmt.power_off()
        self._cell_mgmt.power_on()

        # wait until cellular module becomes ready
        while True:
            try:
                # check whether cellular module is ready
                self._cell_mgmt.sim_status()
                break

            except CellMgmtError:
                sleep(1)
                continue

        # wait another few seconds to ensure module readiness
        sleep(30)

    def _check_alive(self):
        """
        As title.
        """
        next_check = monotonic()
        while not self._stop:
            now = monotonic()
            if now < next_check:
                sleep(1)
                continue

            next_check = now + self._check_period_sec

            if not self._cell_mgmt.status():
                self._log.log_event_cellular_disconnect()
                break

            if not self._ping():
                self._log.log_event_checkalive_failure()
                break


class Manager(object):
    """
    Helper class.
    """

    def __init__(
            self,
            dev_name,
            publish_network_info):

        self._dev_name = dev_name
        self._publish_network_info = publish_network_info

        self._log = Log()

        self._enabled = False
        self._apn = ""
        self._pin = ""
        self._keepalive_enabled = False
        self._keepalive_host = ""
        self._keepalive_period_sec = 60

        self._cell_mgmt = CellMgmt()

        self._connector = None
        self._observer = None

        self._network_information = None
        self._cellular_information = None

    def start(self):
        if self._observer is not None:
            return

        self._observer = CellularObserver()
        self._observer.start(self._set_cellular_information)

    def stop(self):
        if self._observer is not None:
            self._observer.stop()

        if self._connector is not None:
            self._connector.stop()

    def state(self):
        """
        Returns one of:
            "nosim", "pin", "noservice", "ready",
            "connected", "connecting", "connect-failed"
        """
        if self._cellular_information is None:
            return "nosim"

        sim_status = self._cellular_information.sim_status
        if sim_status in ["nosim", "pin"]:
            return sim_status

        if self._cellular_information.signal == 0:
            return "noservice"

        if self._connector is None:
            return "ready"

        if self._network_information is None:
            if self._connector.state == CellularConnector.State.connect_failed:
                return "connect-failed"
            else:
                return "connecting"

        return "connected"

    def cellular_status(self):
        """
        Return dict like:
        {
            "mode": "umts",
            "signal": -87,
            "operator": "Chunghwa Telecom"
            "lac": "2817",
            "cell_id": "01073AEE",
            "pin_retry_remain": 3
        }
        """

        status = {
            "mode": "n/a",
            "signal": 0,
            "operator": "",
            "lac": "",
            "cell_id": "",
            "icc_id": "",
            "imei": "",
            "pin_retry_remain": -1
        }

        cellular_information = self._cellular_information

        if cellular_information is not None:
            status["mode"] = cellular_information.mode
            status["signal"] = cellular_information.signal
            status["operator"] = cellular_information.operator
            status["lac"] = cellular_information.lac
            status["cell_id"] = cellular_information.cell_id
            status["icc_id"] = cellular_information.icc_id
            status["imei"] = cellular_information.imei
            status["pin_retry_remain"] = cellular_information.pin_retry_remain

        return status

    def connection_status(self):
        """
        Return dict like:
        {
            "connected": True,
            "ip": "100.124.244.206",
            "netmask": "255.255.255.252",
            "gateway": "100.124.244.205",
            "dns": ["168.95.1.1", "168.95.192.1"]
        }
        """

        status = {
            "connected": False,
            "ip": "",
            "netmask": "",
            "gateway": "",
            "dns": []
        }

        if self._network_information is None:
            return status

        status["connected"] = True
        status["ip"] = self._network_information.ip
        status["netmask"] = self._network_information.netmask
        status["gateway"] = self._network_information.gateway
        status["dns"] = self._network_information.dns_list

        return status

    def set_pin(self, pin):
        """Return True when PIN verified, otherwise False."""
        if pin != "" and self.state() == "pin":
            if not self._cell_mgmt.set_pin(pin):
                return False

            self._reconnect()

        self._pin = pin
        return True

    def set_configuration(
            self,
            enabled,
            apn,
            pin,
            keepalive_enabled,
            keepalive_host,
            keepalive_period_sec):
        """
        As title.
        """

        if (self._enabled == enabled and
                self._apn == apn and
                self._pin == pin and
                self._keepalive_enabled == keepalive_enabled and
                self._keepalive_host == keepalive_host and
                self._keepalive_period_sec == keepalive_period_sec):
            return

        self._enabled = enabled
        self._apn = apn
        self._pin = pin

        self._keepalive_enabled = keepalive_enabled
        self._keepalive_host = keepalive_host
        self._keepalive_period_sec = keepalive_period_sec

        self._reconnect()

    def _reconnect(self):
        if self._connector:
            self._connector.stop()
            self._connector = None

        if not self._enabled:
            return

        _keepalive_host = None
        _check_period_sec = 60
        if self._keepalive_enabled:
            _keepalive_host = self._keepalive_host
            _check_period_sec = self._keepalive_period_sec

        self._connector = CellularConnector(
            dev_name=self._dev_name,
            apn=self._apn,
            pin=self._pin,
            check_period_sec=_check_period_sec,
            log=self._log,
            keepalive_host=_keepalive_host)

        self._connector.start(self._set_network_information)

    def _set_cellular_information(self, cellular_information):
        self._cellular_information = cellular_information

        if cellular_information is not None:
            self._log.log_cellular_information(cellular_information)

    def _set_network_information(self, network_information):
        """
        network_status should be an instance of NetworkInformation or None
        """
        self._network_information = network_information

        if self._network_information is not None:
            self._publish_network_info(
                self._network_information.ip,
                self._network_information.netmask,
                self._network_information.gateway,
                self._network_information.dns_list)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def dump(ip, netmask, gateway, dns):
        print "ip =", ip
        print "netmask =", netmask
        print "gateway =", gateway
        print "dns =", dns

        check_call(["ip", "route", "add", "default", "via", gateway])

    mgr = Manager("wwan0", dump)
    if not mgr.set_pin("0000"):
        print "pin error"
        exit(1)

    mgr.set_configuration(
        enabled=True,
        apn="internet",
        keepalive_enabled=True,
        keepalive_host="8.8.8.8",
        keepalive_period_sec=10)

    while True:
        sleep(30)
