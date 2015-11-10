"""
cell_mgmt utility wrapper
"""

import logging
import re
from subprocess import check_call, check_output
from subprocess import CalledProcessError
from time import sleep

_logger = logging.getLogger("sanji.cellular")


class CellMgmtError(Exception):
    """CellMgmtError"""
    pass


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
        r"^[a-zA-Z0-9]+ (-[0-9]+) dbm\n$")
    _m_info_regex = re.compile(
        r"^Module=([\S]+)\nWWAN_node=([\S]+)\n")
    _operator_regex = re.compile(
        r"^([\S ]*)\n$")

    def __init__(self):
        self._exe_path = "/sbin/cell_mgmt"

        self._invoke_period_sec = 0

        self._use_shell = False

    def signal(self):
        """
        Returns int as signal strength in dbm.
        """

        _logger.debug("cell_mgmt signal")

        try:
            output = check_output(
                [self._exe_path, "signal"],
                shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

        except CalledProcessError as exc:
            _logger.warning(str(exc))
            raise CellMgmtError

        match = CellMgmt._signal_regex.match(output)
        if not match:
            _logger.error("unexpected output: " + output)
            raise CellMgmtError

        return int(match.group(1))

    def status(self):
        """
        Return boolean as connected or not.
        """

        _logger.debug("cell_mgmt status")

        try:
            check_call([self._exe_path, "status"], shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

            return True

        except CalledProcessError as exc:
            _logger.warning(str(exc))

            # cell_mgmt returns 2 on disconnected
            return False

    def power_off(self):
        """
        Power off Cellular module.
        """
        _logger.debug("cell_mgmt power_off")

        try:
            check_call([self._exe_path, "power_off"], shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

        except CalledProcessError as exc:
            _logger.warning(str(exc))
            raise CellMgmtError

    def power_on(self):
        """
        Power on Cellular module.
        """
        _logger.debug("cell_mgmt power_on")

        try:
            check_call([self._exe_path, "power_on"], shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

        except CalledProcessError as exc:
            _logger.warning(str(exc))
            raise CellMgmtError

    def operator(self):
        """
        Return cellular operator name, like "Chunghwa Telecom"
        """

        _logger.debug("cell_mgmt operator")

        try:
            output = check_output(
                [self._exe_path, "operator"],
                shell=self._use_shell)
            if self._invoke_period_sec != 0:
                sleep(self._invoke_period_sec)

        except CalledProcessError as exc:
            _logger.warning(str(exc))

            raise CellMgmtError

        match = self._operator_regex.match(output)
        if not match:
            raise CellMgmtError

        return match.group(1)


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    cm = CellMgmt()
    while True:
        cm.status()
        cm.signal()

        cm.power_off()
        cm.power_on()
        while True:
            _operator = cm.operator()
            if _operator == "":
                sleep(1)
                continue

            break

        sleep(10)
