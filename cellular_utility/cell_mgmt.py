"""
cell_mgmt utility wrapper
"""

from decorator import decorator
from enum import Enum
import logging
import re
import sh
from sh import ErrorReturnCode, ErrorReturnCode_60
from subprocess import check_call, check_output
from subprocess import CalledProcessError
from threading import RLock
from time import sleep
from traceback import format_exc

_logger = logging.getLogger("sanji.cellular")


class CellMgmtError(Exception):
    """CellMgmtError"""
    pass


@decorator
def handle_called_process_error(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)

    except CalledProcessError:
        _logger.warning(format_exc())

        raise CellMgmtError


BUSY_RETRY_COUNT = 10


@decorator
def retry_on_busy(func, *args, **kwargs):
    for retry in xrange(0, BUSY_RETRY_COUNT + 1):
        try:
            return func(*args, **kwargs)

        except CalledProcessError as exc:
            if (exc.returncode == 60 and
                    retry < BUSY_RETRY_COUNT):

                _logger.debug("cell_mgmt busy retry: " + str(retry))

                sleep(10)
                continue

            else:
                _logger.warning(format_exc())
                raise

        except ErrorReturnCode_60 as exc:
            if retry < BUSY_RETRY_COUNT:
                _logger.debug("cell_mgmt busy retry: {}".format(str(retry)))

                sleep(10)
                continue

            else:
                _logger.warning(format_exc())
                raise

        except ErrorReturnCode:
            _logger.warning(format_exc())
            raise


@decorator
def critical_section(func, *args, **kwargs):
    # lock by process
    with CellMgmt._lock:
        return func(*args, **kwargs)


class MInfo(object):
    def __init__(
            self,
            module,
            wwan_node,
            lac=None,
            cell_id=None,
            icc_id=None,
            imei=None,
            qmi_port=None):
        self._module = module
        self._wwan_node = wwan_node
        self._lac = "" if lac is None else lac
        self._cell_id = "" if cell_id is None else cell_id
        self._icc_id = "" if icc_id is None else icc_id
        self._imei = "" if imei is None else imei

        self._qmi_port = qmi_port

    @property
    def module(self):
        return self._module

    @property
    def wwan_node(self):
        return self._wwan_node

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
    def qmi_port(self):
        return self._qmi_port


class SimStatus(Enum):
    nosim = 0
    pin = 1
    ready = 2


class Signal(object):
    def __init__(
            self,
            mode=None,
            rssi_dbm=None):
        self._mode = "none" if mode is None else mode
        self._rssi_dbm = 0 if rssi_dbm is None else rssi_dbm

    @property
    def mode(self):
        return self._mode

    @property
    def rssi_dbm(self):
        return self._rssi_dbm


class CellMgmt(object):
    """
    cell_mgmt utilty wrapper
    """

    _start_ip_regex = re.compile(
        r"IP=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\n")
    _start_netmask_regex = re.compile(
        r"SubnetMask=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\n")
    _start_gateway_regex = re.compile(
        r"Gateway=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\n")
    _start_dns_regex = re.compile(
        r"DNS=([0-9\. ]*)\n")
    _signal_regex = re.compile(
        r"^([a-zA-Z0-9]+) (-[0-9]+) dbm\n$")
    _m_info_regex = re.compile(
        r"^Module=([\S ]+)\n"
        r"WWAN_node=([\S]+)\n"
        r"AT_port=[\S]*\n"
        r"GPS_port=[\S]*\n"
        r"LAC=([\S]*)\n"
        r"CellID=([\S]*)\n"
        r"ICC-ID=([\S]*)\n"
        r"IMEI=([\S]*)\n"
        r"QMI_port=([\S]*)\n")
    _operator_regex = re.compile(
        r"^([\S ]*)\n$")
    _sim_status_ready_regex = re.compile(
        r"^\+CPIN:\s*READY$")
    _sim_status_sim_pin_regex = re.compile(
        r"^\+CPIN:\s*SIM\s+PIN$")

    _pin_retry_remain_regex = re.compile(
        r"\[[\S]+\][\S ]+\n"
        r"\[[\S]+\] PIN1:\n"
        r"[\s]*Status:[\s]*[\S]*\n"
        r"[\s]*Verify:[\s]*([0-9]+)\n"
    )

    _lock = RLock()

    def __init__(self):
        self._exe_path = "/sbin/cell_mgmt"
        self._cell_mgmt = sh.cell_mgmt
        self._qmicli = sh.qmicli

        self._invoke_period_sec = 0

        self._use_shell = False

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def start(self, apn, pin=None):
        """
        Start cellular connection.
        Return dict like:
            {
                "ip": "10.24.42.11",
                "netmask": "255.255.255.252",
                "gateway": "10.24.42.10",
                "dns": ["168.95.1.1"]
            }
        """

        _logger.debug("cell_mgmt start")

        args = [
            "start", "ignore-dns-gw",
            "APN=" + apn,
            "Username=",
            "Password="
        ]
        if pin is not None:
            args.append("PIN=" + pin)
        else:
            args.append("PIN=")

        output = self._cell_mgmt(*args)
        output = str(output)
        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = self._start_ip_regex.search(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        ip_ = match.group(1)

        match = self._start_netmask_regex.search(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        netmask = match.group(1)

        match = self._start_gateway_regex.search(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        gateway = match.group(1)

        match = self._start_dns_regex.search(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        dns = match.group(1).split(" ")

        return {
            "ip": ip_,
            "netmask": netmask,
            "gateway": gateway,
            "dns": dns
        }

    @critical_section
    @retry_on_busy
    def stop(self):
        """
        Stops cellular connection.
        """

        _logger.debug("cell_mgmt stop")

        try:
            self._cell_mgmt("stop")
        except ErrorReturnCode:
            _logger.warning(format_exc() + ", ignored")

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def signal(self):
        """Returns an instance of Signal."""

        _logger.debug("cell_mgmt signal")

        output = self._cell_mgmt("signal")
        output = str(output)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = CellMgmt._signal_regex.match(output)
        if match:
            return Signal(
                mode=match.group(1),
                rssi_dbm=int(match.group(2)))

        _logger.warning("unexpected output: " + output)
        # signal out of range
        return Signal()

    @critical_section
    def status(self):
        """
        Return boolean as connected or not.
        """

        _logger.debug("cell_mgmt status")

        for retry in xrange(0, BUSY_RETRY_COUNT + 1):
            try:
                self._cell_mgmt("status")

                return True

            except ErrorReturnCode_60:
                if retry < BUSY_RETRY_COUNT:
                    sleep(10)
                    continue

            except ErrorReturnCode:
                break

        return False

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def power_off(self):
        """
        Power off Cellular module.
        """
        _logger.debug("cell_mgmt power_off")

        self._cell_mgmt("power_off")

        # sleep to make sure GPIO is pulled down for enough time
        sleep(1)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def power_on(self, timeout_sec=60):
        """
        Power on Cellular module.
        """
        _logger.debug("cell_mgmt power_on")

        sh.timeout(str(timeout_sec), "cell_mgmt", "power_on")

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def m_info(self):
        """Return instance of MInfo."""

        _logger.debug("cell_mgmt m_info")

        output = self._cell_mgmt("m_info")
        output = str(output)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = self._m_info_regex.match(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        qmi_port = match.group(7)
        if qmi_port == "":
            qmi_port = None

        return MInfo(
            module=match.group(1),
            wwan_node=match.group(2),
            lac=match.group(3),
            cell_id=match.group(4),
            icc_id=match.group(5),
            imei=match.group(6),
            qmi_port=qmi_port)

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def operator(self):
        """
        Return cellular operator name, like "Chunghwa Telecom"
        """

        _logger.debug("cell_mgmt operator")

        output = self._cell_mgmt("operator")
        output = str(output)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = self._operator_regex.match(output)
        if not match:
            _logger.warning("unexpected output: {}".format(output))
            raise CellMgmtError

        return match.group(1)

    @critical_section
    @retry_on_busy
    def set_pin(self, pin):
        """
        Return True if PIN unlocked.
        """

        _logger.debug("cell_mgmt set_pin")
        try:
            self._cell_mgmt("set_pin", pin)

            return True

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            return False

    @critical_section
    @retry_on_busy
    def sim_status(self):
        """
        Returns instance of SimStatus.
        """

        """
        'cell_mgmt sim_status' exit non-zero when SIM card not inserted.
        """

        _logger.debug("cell_mgmt sim_status")
        try:
            output = self._cell_mgmt("sim_status")
            output = str(output)

            if self._sim_status_ready_regex.match(output):
                return SimStatus.ready
            elif self._sim_status_sim_pin_regex.match(output):
                return SimStatus.pin

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            return SimStatus.nosim

    @critical_section
    @handle_called_process_error
    def get_pin_retry_remain(self):
        """
        Return the number of retries left for PIN.
        """

        _logger.debug("get_pin_retry_remain")

        qmi_port = self.m_info().qmi_port
        if qmi_port is None:
            _logger.warning("no qmi-port exist, return -1")
            return -1

        _logger.debug("qmicli -d " + qmi_port + " --dms-uim-get-pin-status")
        output = self._qmicli("-d", qmi_port, "--dms-uim-get-pin-status")
        output = str(output)

        match = CellMgmt._pin_retry_remain_regex.match(output)
        if not match:
            _logger.warning("unexpected output: {}".format(output))
            raise CellMgmtError

        return int(match.group(1))


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    cm = CellMgmt()
    while True:
        for _retry in range(0, 10):
            try:
                cm.stop()
                cm.start(apn="internet", pin="0000")
                break

            except CellMgmtError as err:
                _logger.error(str(err))

                continue

        cm.status()

        cm.stop()
        cm.power_off()
        cm.power_on()
        while True:
            _operator = cm.operator()
            if _operator == "":
                sleep(1)
                continue

            break

        sleep(10)
