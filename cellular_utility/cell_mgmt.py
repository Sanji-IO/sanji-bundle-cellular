"""
cell_mgmt utility wrapper
"""

from decorator import decorator
from enum import Enum
import os
import logging
import re
import sh
from sh import ErrorReturnCode, ErrorReturnCode_60, TimeoutException
from subprocess import CalledProcessError
import thread
from threading import RLock
from time import sleep
from traceback import format_exc
from retrying import retry as retrying

_logger = logging.getLogger("sanji.cellular")

tool_path = os.path.dirname(os.path.realpath(__file__))


class CellMgmtError(Exception):
    """CellMgmtError"""
    pass


@decorator
def handle_error_return_code(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)

    except ErrorReturnCode:
        _logger.warning(format_exc())
    except TimeoutException:
        _logger.warning("qmicli TimeoutException")
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
    if CellMgmt._lock._RLock__owner == thread.get_ident() \
            or CellMgmt._lock._RLock__owner is None:
        with CellMgmt._lock:
            return func(*args, **kwargs)

    # lock by process
    timeout = 120
    while timeout > 0:
        if CellMgmt._lock.acquire(blocking=False) is True:
            try:
                return func(*args, **kwargs)
            finally:
                CellMgmt._lock.release()
        else:
            timeout = timeout - 1
            sleep(1)
            continue

    _logger.warning("cell_mgmt timeout, release lock")
    try:
        os.remove("/tmp/cell_mgmt.lock")
    except OSError as e:
        _logger.warning(str(e))
    except:
        _logger.warning(format_exc())


def sh_default_timeout(func, timeout):
    def _sh_default_timeout(*args, **kwargs):
        if kwargs.get("_timeout", None) is None:
            kwargs.update({"_timeout": timeout})
        return func(*args, **kwargs)
    return _sh_default_timeout


class NetworkInformation(object):
    def __init__(
            self,
            ip,
            netmask,
            gateway,
            dns_list):
        if (not isinstance(ip, str) or
                not isinstance(netmask, str) or
                not isinstance(gateway, str)):
            raise ValueError

        if not isinstance(dns_list, list):
            raise ValueError

        for dns in dns_list:
            if not isinstance(dns, str):
                raise ValueError

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
            rssi_dbm=None,
            ecio_dbm=None,
            csq=None):
        self._mode = "none" if mode is None else mode
        self._rssi_dbm = 0 if rssi_dbm is None else rssi_dbm
        self._ecio_dbm = 0.0 if ecio_dbm is None else ecio_dbm
        self._csq = 0 if csq is None else csq

    @property
    def mode(self):
        return self._mode

    @property
    def csq(self):
        return self._csq

    @property
    def rssi_dbm(self):
        return self._rssi_dbm

    @property
    def ecio_dbm(self):
        return self._ecio_dbm


class CellularLocation(object):
    def __init__(
            self,
            cell_id=None,
            lac=None):
        if (not isinstance(cell_id, str) or
                not isinstance(lac, str)):
            raise ValueError

        self._cell_id = cell_id
        self._lac = lac

    @property
    def cell_id(self):
        return self._cell_id

    @property
    def lac(self):
        return self._lac


class CellularNumber(object):
    def __init__(
            self,
            number=None):
        if not isinstance(number, str):
            raise ValueError

        self._number = number

    @property
    def number(self):
        return self._number


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
        r"^([\S]+) (-[0-9]+) dbm\n$")
    _signal_adv_regex = re.compile(
        r"^CSQ: ([0-9]+)\n"
        r"RSSI: ([\S]+) (-[0-9]+) dBm\n"
        r"EcIo: ([\S]+) (-[0-9.]+) dBm\n")
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
        r"[\s\S]*PIN1 state: '([\S]+)'\n"
        r"[\n\t ]*PIN1 retries: '([0-9]+)'\n"
        r"[\n\t ]*PUK1 retries: '([0-9]+)'\n"
    )
    _attach_status_regex = re.compile(
        r"PS: attached\n"
    )

    _number_regex = re.compile(
        r"^([^\n]*)[\n]{0,1}")

    _at_response_ok_regex = re.compile(
        r"^[\r\n]*([+\S\s :]*)[\r\n]+OK[\r\n]*$")
    _at_response_err_regex = re.compile(
        r"^[\r\n]*ERROR[\r\n]*$")
    _at_response_cme_err_regex = re.compile(
        r"^[\r\n]*\+CME ERROR: ([\S ]*)[\r\n]*$")

    _split_param_by_comma_regex = re.compile(
        r",{0,1}\"{0,1}([^\s\",]*)\"{0,1},{0,1}")

    _lock = RLock()

    def __init__(self):
        self._exe_path = "/sbin/cell_mgmt"

        # Add default timeout to cell_mgmt and qmicli
        # will raise TimeoutException
        self._cell_mgmt = sh_default_timeout(sh.cell_mgmt, 70)
        self._qmicli = sh_default_timeout(
            sh.Command(tool_path + "/call-qmicli.sh"), 70)

        self._invoke_period_sec = 0

        self._use_shell = False

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    @retrying(
        stop_max_attempt_number=10, wait_random_min=500, wait_random_max=1500)
    def at(self, cmd):
        """
        Send AT command.
        Return the AT command response with dict like
            {
                "status": "ok",    # ok, err, cme-err
                "info": "+CFUN: 1"   # or cme error like: SIM not inserted
            }
        """
        _logger.debug("cell_mgmt at {}".format(cmd))
        output = self._cell_mgmt("at", cmd)
        output = str(output)

        match = self._at_response_ok_regex.match(output)
        if match:
            return {"status": "ok", "info": match.group(1).rstrip("\r\n")}

        match = self._at_response_cme_err_regex.match(output)
        if match:
            return {"status": "cme-err", "info": match.group(1).rstrip("\r\n")}

        match = self._at_response_err_regex.match(output)
        if match:
            return {"status": "err", "info": ""}

        _logger.warning("unexpected output: " + output)
        raise CellMgmtError

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    def attach(self):
        """
        Return True if service attached.
        """

        _logger.debug("cell_mgmt attach_status")
        try:
            # CS: attached/detached
            # PS: attached/detached
            # PS should be attached
            output = str(self._cell_mgmt("attach_status"))
            if self._attach_status_regex.search(output):
                return True
            return False

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            raise CellMgmtError

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    def start(self, apn):
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
            "Password=",
            "PIN="
        ]

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

        return NetworkInformation(
            ip=ip_,
            netmask=netmask,
            gateway=gateway,
            dns_list=dns)

    @critical_section
    @handle_error_return_code
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
    @handle_error_return_code
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
    @handle_error_return_code
    @retry_on_busy
    def signal_adv(self):
        """Returns an instance of Signal."""

        _logger.debug("cell_mgmt signal_adv")

        output = self._cell_mgmt("signal_adv")
        output = str(output)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = CellMgmt._signal_adv_regex.match(output)
        if match:
            return Signal(
                csq=int(match.group(1)),
                mode=match.group(2),
                rssi_dbm=int(match.group(3)),
                ecio_dbm=float(match.group(5)))

        _logger.warning("unexpected output: " + output)
        # signal out of range
        return Signal()

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    def number(self):
        """Returns an instance of CellularNumber."""

        _logger.debug("cell_mgmt number")

        output = self._cell_mgmt("number")
        output = str(output)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

        match = CellMgmt._number_regex.match(output)
        if match:
            return CellularNumber(
                number=match.group(1))

        _logger.warning("unexpected output: " + output)
        return CellularNumber()

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

            except (ErrorReturnCode_60, TimeoutException):
                if retry < BUSY_RETRY_COUNT:
                    sleep(10)
                    continue

            except ErrorReturnCode:
                break

        return False

    @handle_error_return_code
    @retry_on_busy
    def _power_off(self, force=False):
        """
        Power off Cellular module.
        """
        _logger.debug("cell_mgmt power_off")

        self._cell_mgmt("power_off", "force" if force else "")

        # sleep to make sure GPIO is pulled down for enough time
        sleep(1)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

    @handle_error_return_code
    @retry_on_busy
    def _power_on(self, force=False, timeout_sec=60):
        """
        Power on Cellular module.
        """
        _logger.debug("cell_mgmt power_on")

        self._cell_mgmt(
            "power_on", "force" if force else "", _timeout=timeout_sec)

        if self._invoke_period_sec != 0:
            sleep(self._invoke_period_sec)

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    def power_cycle(self, force=False, timeout_sec=60):
        """
        Power cycle Cellular module.
        """
        self._power_off(force)
        sleep(1)
        self._power_on(force, timeout_sec)

    @critical_section
    @handle_error_return_code
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
    @handle_error_return_code
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
    @handle_error_return_code
    @retry_on_busy
    def pdp_context_list(self):
        """
        Return PDP context list.

        Response of "get_profiles"
            <id>,<apn>,<type>
        Example:
            1,internet,IP
            2,TPC,IPV4V6
        """
        _logger.debug("pdp_context_list: 'at+cgdcont?'")
        try:
            pdpc_list = []
            res = self._cell_mgmt("get_profiles")

            for item in res.splitlines(True):
                pdpc = self._split_param_by_comma_regex.findall(item)
                if len(pdpc) <= 3:
                    continue
                pdpc_list.append(
                    {"id": int(pdpc[0]),
                     "type": "ipv4" if pdpc[2] == "IP"
                             else pdpc[2].lower(),
                     "apn": pdpc[1]})
            return pdpc_list

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            raise CellMgmtError

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    @retrying(
        stop_max_attempt_number=3, wait_random_min=500, wait_random_max=1500)
    def set_pdp_context(self, id, apn, type="ipv4v6"):
        """
        Return True if PDP context set.
        """
        pdp_type = "ip" if type == "ipv4" else type

        _logger.debug(
            "cell_mgmt set_profile {} {} {}".format(id, pdp_type, apn))
        try:
            self._cell_mgmt("set_profile", id, apn, pdp_type)

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            raise CellMgmtError

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    def set_pin(self, pin):
        """
        Return True if PIN unlocked.
        """

        _logger.debug("cell_mgmt unlock_pin")
        try:
            self._cell_mgmt("unlock_pin", pin)

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            raise CellMgmtError

    @critical_section
    @handle_error_return_code
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
            else:
                return SimStatus.nosim

        except ErrorReturnCode_60:
            raise

        except ErrorReturnCode:
            return SimStatus.nosim

    @critical_section
    @handle_error_return_code
    def get_pin_retry_remain(self):
        """
        Return the number of retries left for PIN.
        """

        _logger.debug("get_pin_retry_remain")

        qmi_port = self.m_info().qmi_port
        if qmi_port is None:
            _logger.warning("no qmi-port exist, return -1")
            return -1

        _logger.debug("qmicli -p -d " + qmi_port + " --uim-get-card-status")
        output = self._qmicli("-p", "-d", qmi_port, "--uim-get-card-status")
        output = str(output)

        match = CellMgmt._pin_retry_remain_regex.match(output)
        if not match:
            _logger.warning("unexpected output: {}".format(output))
            raise CellMgmtError

        if match.group(1) == "disabled":
            return -1

        return int(match.group(2))

    @critical_section
    @handle_error_return_code
    def get_cellular_location(self):
        """
        Return CellularLocation instance.
        """

        _logger.debug("get_cellular_location")

        minfo = self.m_info()
        return CellularLocation(
            cell_id=minfo.cell_id,
            lac=minfo.lac)


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
        cm.power_cycle()
        while True:
            _operator = cm.operator()
            if _operator == "":
                sleep(1)
                continue

            break

        sleep(10)
