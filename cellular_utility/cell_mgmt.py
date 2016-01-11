"""
cell_mgmt utility wrapper
"""

from decorator import decorator
import logging
import re
from subprocess import check_call, check_output
from subprocess import CalledProcessError
from threading import Lock
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


@decorator
def critical_section(func, *args, **kwargs):
    # lock by process
    with CellMgmt._lock:
        return func(*args, **kwargs)


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
        r"IMEI=([\S]+)\n")
    _operator_regex = re.compile(
        r"^([\S ]*)\n$")
    _sim_status_ready_regex = re.compile(
        r"^\+CPIN:\s*READY$")
    _sim_status_sim_pin_regex = re.compile(
        r"^\+CPIN:\s*SIM\s+PIN$")

    _lock = Lock()

    def __init__(self):
        self._exe_path = "/sbin/cell_mgmt"

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

        cmd = [
            self._exe_path, "start", "ignore-dns-gw",
            "APN=" + apn,
            "Username=",
            "Password="
        ]
        if pin is not None:
            cmd.append("PIN=" + pin)
        else:
            cmd.append("PIN=")

        output = check_output(cmd, shell=self._use_shell)
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
            check_output([self._exe_path, "stop"], shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

        except CalledProcessError as exc:
            if exc.returncode == 60:
                raise

            _logger.warning(format_exc() + ", ignored")

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def signal(self):
        """
        Returns a dict like:
            {
                "mode": "umts",
                "rssi_dbm": -80
            }
        """

        _logger.debug("cell_mgmt signal")

        output = check_output(
            [self._exe_path, "signal"],
            shell=self._use_shell)
        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = CellMgmt._signal_regex.match(output)
        if not match:
            _logger.error("unexpected output: " + output)
            raise CellMgmtError

        return {
            "mode": match.group(1),
            "rssi_dbm": int(match.group(2))
        }

    @critical_section
    def status(self):
        """
        Return boolean as connected or not.
        """

        _logger.debug("cell_mgmt status")

        for retry in xrange(0, BUSY_RETRY_COUNT + 1):
            try:
                check_call([self._exe_path, "status"], shell=self._use_shell)
                if self._invoke_period_sec != 0:
                    sleep(self._invoke_period_sec)

                return True

            except CalledProcessError as exc:
                if (exc.returncode == 60 and
                        retry < BUSY_RETRY_COUNT):
                    sleep(10)
                    continue

                _logger.debug(str(exc))
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

        check_call([self._exe_path, "power_off"], shell=self._use_shell)

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

        check_call(
            [
                "timeout",
                str(timeout_sec),
                self._exe_path,
                "power_on"
            ],
            shell=self._use_shell)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def m_info(self):
        """
        Return dict like:
            {
                "Module": "MC7304",
                "WWAN_node": "wwan0",
                "LAC": "2817",
                "CellID": "01073AEE"
                "ICC-ID": "",
                "IMEI": "356853050370859"
            }
        """

        _logger.debug("cell_mgmt m_info")

        output = check_output(
            [self._exe_path, "m_info"],
            shell=self._use_shell)
        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = self._m_info_regex.match(output)
        if not match:
            _logger.warning("unexpected output: " + output)
            raise CellMgmtError

        return {
            "Module": match.group(1),
            "WWAN_node": match.group(2),
            "LAC": match.group(3),
            "CellID": match.group(4),
            "ICC-ID": match.group(5),
            "IMEI": match.group(6)
        }

    @critical_section
    @handle_called_process_error
    @retry_on_busy
    def operator(self):
        """
        Return cellular operator name, like "Chunghwa Telecom"
        """

        _logger.debug("cell_mgmt operator")

        output = check_output(
            [self._exe_path, "operator"],
            shell=self._use_shell)
        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = self._operator_regex.match(output)
        if not match:
            _logger.warning("unexpected output: " + output)
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
            check_call(
                [self._exe_path, "set_pin", pin],
                shell=self._use_shell)

            return True

        except CalledProcessError:
            return False

    @critical_section
    @retry_on_busy
    def sim_status(self):
        """
        Returns one of:
            "nosim"
            "pin"
            "ready"
        """

        """
        'cell_mgmt sim_status' exit non-zero when SIM card not inserted.
        """

        _logger.debug("cell_mgmt sim_status")
        try:
            output = check_output(
                [self._exe_path, "sim_status"],
                shell=self._use_shell)

            if self._sim_status_ready_regex.match(output):
                return "ready"
            elif self._sim_status_sim_pin_regex.match(output):
                return "pin"

        except CalledProcessError as exc:
            if exc.returncode == 60:
                raise

            return "nosim"


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
