"""
Helper library.
"""

import logging
import sys

from monotonic import monotonic
from subprocess import check_call, CalledProcessError
from threading import Thread
from time import sleep
from traceback import format_exc, print_exc

from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError
from cellular_utility.event import Log

_logger = logging.getLogger("sanji.cellular")


class CellularInformation(object):
    def __init__(
            self,
            signal,
            operator,
            lac,
            cell_id):
        self._signal = signal
        self._operator = operator
        self._lac = lac
        self._cell_id = cell_id

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

                try:
                    signal = self._cell_mgmt.signal()

                    operator = self._cell_mgmt.operator()

                    m_info = self._cell_mgmt.m_info()

                    update_cellular_information(CellularInformation(
                        signal,
                        operator,
                        m_info["LAC"],
                        m_info["CellID"]))

                except CellMgmtError:
                    _logger.warning(format_exc())
                    continue

        self._stop = False
        self._thread = Thread(target=main_thread)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()


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

    PING_TIMEOUT_SEC = 10

    def __init__(
            self,
            apn,
            pin,
            check_period_sec,
            log,
            keepalive_host=None):

        self._apn = apn
        self._pin = pin
        self._check_period_sec = check_period_sec
        self._keepalive_host = keepalive_host
        self._log = log

        self._cell_mgmt = CellMgmt()

        self._connect_thread = None
        self._stop = False

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
                    connected = False

                    # connect Cellular
                    for retry in range(0, 4):
                        update_network_information(None)

                        if self._stop:
                            break

                        self._log.log_event_connect_begin()

                        self._cell_mgmt.stop()

                        try:
                            network_info = self._cell_mgmt.start(
                                apn=self._apn,
                                pin=self._pin)

                        except CellMgmtError:
                            self._log.log_event_connect_failure()

                            print_exc()

                            sleep(10)

                            continue

                        if not self._cell_mgmt.status():
                            self._log.log_event_connect_failure()

                            sleep(10)
                            continue

                        # publish cellular information here
                        connected = True
                        network_information = NetworkInformation(
                            network_info["ip"],
                            network_info["netmask"],
                            network_info["gateway"],
                            network_info["dns"])
                        update_network_information(network_information)

                        self._log.log_event_connect_success(
                            network_information)

                        # sleep awhile to let ip-route take effect
                        sleep(3)
                        break

                    if self._stop:
                        break

                    # retry count exceeded, power-cycle cellular module
                    if not connected:
                        _logger.warning("power-cycle cellular module")

                        self._log.log_event_power_cycle()

                        self._cell_mgmt.stop()
                        self._cell_mgmt.power_off()
                        self._cell_mgmt.power_on()

                        # wait until cellular module becomes ready
                        while True:
                            try:
                                # check whether cellular module is ready
                                self._cell_mgmt.signal()
                                break

                            except CellMgmtError:
                                sleep(1)
                                continue

                        # wait another 10 seconds to ensure module readiness
                        sleep(10)

                        continue

                    # cellular connected, start keepalive
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

                except CellMgmtError:
                    print_exc()
                    continue

            self._cell_mgmt.stop()
            self._log.log_event_cellular_disconnect()
            update_network_information(None)

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

    def _ping(self):
        """
        Return whether ping succeeded.
        """
        if not self._keepalive_host:
            return True

        try:
            check_call([
                "ping",
                "-c", "3",
                "-W", str(self.PING_TIMEOUT_SEC),
                self._keepalive_host])
            return True

        except CalledProcessError:
            return False


class PinError(Exception):
    """ Raised when PIN code verification fails """
    pass


class Manager(object):
    """
    Helper class.
    """

    def __init__(
            self,
            publish_network_info):

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

        # if SIM card not found, don't do observation
        if self._cell_mgmt.sim_status() == "nosim":
            self._log.log_nosim()
            return

        self._observer = CellularObserver()
        self._observer.start(self._set_cellular_information)

    def stop(self):
        if self._observer is not None:
            self._observer.stop()

        if self._connector is not None:
            self._connector.stop()

    def cellular_status(self):
        """
        Return dict like:
        {
            "signal": -87,
            "operator": "Chunghwa Telecom"
            "lac": "2817",
            "cell_id": "01073AEE"
        }
        """

        status = {
            "signal": 0,
            "operator": "",
            "lac": "",
            "cell_id": ""
        }

        cellular_information = self._cellular_information

        if cellular_information is not None:
            status["signal"] = cellular_information.signal
            status["operator"] = cellular_information.operator
            status["lac"] = cellular_information.lac
            status["cell_id"] = cellular_information.cell_id

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
        if pin != "":
            if not self._cell_mgmt.set_pin(pin):
                return False

        self._pin = pin
        return True

    def set_configuration(
            self,
            enabled,
            apn,
            keepalive_enabled,
            keepalive_host,
            keepalive_period_sec):
        """
        As title.
        """

        if (self._enabled == enabled and
                self._apn == apn and
                self._keepalive_enabled == keepalive_enabled and
                self._keepalive_host == keepalive_host and
                self._keepalive_period_sec == keepalive_period_sec):
            return

        self._enabled = enabled
        self._apn = apn

        self._keepalive_enabled = keepalive_enabled
        self._keepalive_host = keepalive_host
        self._keepalive_period_sec = keepalive_period_sec

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
            apn=self._apn,
            pin=self._pin,
            check_period_sec=_check_period_sec,
            log=self._log,
            keepalive_host=_keepalive_host)

        self._connector.start(self._set_network_information)

    def _set_cellular_information(self, cellular_information):
        self._cellular_information = cellular_information

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

    mgr = Manager(dump)
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
