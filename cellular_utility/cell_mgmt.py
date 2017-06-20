"""
cell_mgmt utility wrapper
"""

from decorator import decorator
from enum import Enum
import os
import logging
import re
import sh
from sh import (
    ErrorReturnCode, ErrorReturnCode_1, ErrorReturnCode_2, ErrorReturnCode_3,
    ErrorReturnCode_4, ErrorReturnCode_99, ErrorReturnCode_60, TimeoutException
)
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

    except ErrorReturnCode_2:
        _logger.warning("profile not found")
    except ErrorReturnCode_3:
        _logger.warning("operation not support")
    except ErrorReturnCode_4:
        _logger.warning("invalid input")
    except ErrorReturnCode_99:
        _logger.warning("module may crash")
    except ErrorReturnCode:
        _logger.warning(format_exc())
    except TimeoutException:
        _logger.warning("TimeoutException")
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

    _logger.warning("cell_mgmt timeout")


def sh_default_timeout(func, timeout):
    def _sh_default_timeout(*args, **kwargs):
        if kwargs.get("_timeout", None) is None:
            kwargs.update({"_timeout": timeout})
        return func(*args, **kwargs)
    return _sh_default_timeout


class NetworkInformation(object):
    def __init__(
            self,
            status,
            ip,
            netmask,
            gateway,
            dns_list):
        if (not isinstance(status, bool) or
                not isinstance(ip, str) or
                not isinstance(netmask, str) or
                not isinstance(gateway, str)):
            raise ValueError

        if not isinstance(dns_list, list):
            raise ValueError

        for dns in dns_list:
            if not isinstance(dns, str):
                raise ValueError

        self._status = status
        self._ip = ip
        self._netmask = netmask
        self._gateway = gateway
        self._dns_list = dns_list

    @property
    def status(self):
        return self._status

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


class CellularModuleIds(object):
    def __init__(
            self,
            imei="",
            esn=""):
        if (not isinstance(imei, str) or
                not isinstance(esn, str)):
            raise ValueError

        self._imei = imei
        self._esn = esn

    @property
    def imei(self):
        return self._imei

    @property
    def esn(self):
        return self._esn


class CellularSimInfo(object):
    def __init__(
            self,
            iccid="",
            imsi=""):
        if (not isinstance(iccid, str) or
                not isinstance(imsi, str)):
            raise ValueError

        self._iccid = iccid
        self._imsi = imsi

    @property
    def iccid(self):
        return self._iccid

    @property
    def imsi(self):
        return self._imsi


class CellularLocation(object):
    def __init__(
            self,
            cell_id="",
            lac="",
            tac="",
            bid="",
            nid=""):
        if (not isinstance(cell_id, str) or
                not isinstance(lac, str) or
                not isinstance(tac, str) or
                not isinstance(bid, str) or
                not isinstance(nid, str)):
            raise ValueError

        self._cell_id = cell_id
        self._lac = lac
        self._tac = tac
        self._bid = bid
        self._nid = nid

    @property
    def cell_id(self):
        return self._cell_id

    @property
    def lac(self):
        return self._lac

    @property
    def tac(self):
        return self._tac

    @property
    def bid(self):
        return self._bid

    @property
    def nid(self):
        return self._nid


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

    _module_ids_imei_regex = re.compile(
        r"IMEI: ([\S]*)\n"
    )
    _module_ids_esn_regex = re.compile(
        r"ESN: ([\S]*)\n"
    )

    _sim_info_iccid_regex = re.compile(
        r"ICC-ID: ([\S]*)\n"
    )
    _sim_info_imsi_regex = re.compile(
        r"IMSI: ([\S]*)\n"
    )

    _location_info_lac_regex = re.compile(
        r"LAC: ([\S]*)\n"
    )
    _location_info_tac_regex = re.compile(
        r"TAC: ([\S]*)\n"
    )
    _location_info_cellid_regex = re.compile(
        r"CellID: ([\S]*)\n"
    )
    _location_info_nid_regex = re.compile(
        r"NID: ([\S]*)\n"
    )
    _location_info_bid_regex = re.compile(
        r"BID: ([\S]*)\n"
    )

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

        # Add default timeout to cell_mgmt
        # will raise TimeoutException
        self._cell_mgmt = sh_default_timeout(sh.cell_mgmt, 70)

        self._invoke_period_sec = 0

        self._use_shell = False

    @critical_section
    @handle_error_return_code
    @retry_on_busy
    @retrying(
        stop_max_attempt_number=10, wait_random_min=500, wait_random_max=1500)
    def at(self, cmd, timeout=None):
        """
        Send AT command.
        Return the AT command response with dict like
            {
                "status": "ok",    # ok, err, cme-err
                "info": "+CFUN: 1"   # or cme error like: SIM not inserted
            }
        """
        _logger.debug("cell_mgmt at {}".format(cmd))
        if timeout is None:
            output = self._cell_mgmt("at", cmd)
        else:
            output = self._cell_mgmt("at", cmd, timeout)
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
        # CS: attached/detached
        # PS: attached/detached
        # PS should be attached
        output = str(self._cell_mgmt("attach_status"))
        if self._attach_status_regex.search(output):
            return True
        return False

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
            status=True,
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
        return NetworkInformation(
            status=False,
            ip="",
            netmask="",
            gateway="",
            dns_list=[])

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
    def status(self):
        """
        Return boolean as connected or not.
        """

        _logger.debug("cell_mgmt status")

        try:
            self._cell_mgmt("status")
            return True
        except ErrorReturnCode_1:
            return False

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

    @critical_section
    @handle_error_return_code
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

    @critical_section
    @handle_error_return_code
    def set_pin(self, pin):
        """
        Return True if PIN unlocked.
        """

        _logger.debug("cell_mgmt unlock_pin")
        try:
            self._cell_mgmt("unlock_pin", pin)

        except ErrorReturnCode_60:
            raise

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

        except ErrorReturnCode:
            return SimStatus.nosim

    @critical_section
    @handle_error_return_code
    def get_pin_retry_remain(self):
        """
        Return the number of retries left for PIN.
        """

        _logger.debug("cell_mgmt pin_retries")
        output = self._cell_mgmt("pin_retries")
        return int(output)

    @critical_section
    @handle_error_return_code
    def get_cellular_module_ids(self):
        """
        Return CellularModuleIds instance.
        """
        imei = ""
        esn = ""

        _logger.debug("cell_mgmt module_ids")

        # `cell_mgmt module_ids`
        # IMEI: xxx
        # ESN: xxx
        output = str(self._cell_mgmt("module_ids"))
        found = self._module_ids_imei_regex.search(output)
        if found:
            imei = found.group(1)

        found = self._module_ids_esn_regex.search(output)
        if found:
            esn = found.group(1)

        return CellularModuleIds(
            imei=imei,
            esn=esn)

    @critical_section
    @handle_error_return_code
    def get_cellular_sim_info(self):
        """
        Return CellularSimInfo instance.
        """
        iccid = ""
        imsi = ""

        _logger.debug("cell_mgmt iccid")
        _logger.debug("cell_mgmt imsi")

        # `cell_mgmt iccid`
        # ICCID: xxx
        output = str(self._cell_mgmt("iccid"))
        found = self._sim_info_iccid_regex.search(output)
        if found:
            iccid = found.group(1)

        # `cell_mgmt imsi`
        # IMSI: xxx
        output = str(self._cell_mgmt("imsi"))
        found = self._sim_info_imsi_regex.search(output)
        if found:
            imsi = found.group(1)

        return CellularSimInfo(
            iccid=iccid,
            imsi=imsi)

    @critical_section
    @handle_error_return_code
    def get_cellular_location(self):
        """
        Return CellularLocation instance.
        """
        cellid = ""
        lac = ""
        tac = ""
        nid = ""
        bid = ""

        _logger.debug("cell_mgmt location_info")

        # [umts]
        # LAC: xxx
        # CellID: xxx
        #
        # [lte]
        # TAC: xxx
        # CellID: xxx
        #
        # [cdma]
        # NID: xxx
        # BID: xxx
        output = str(self._cell_mgmt("location_info"))
        found = self._location_info_lac_regex.search(output)
        if found:
            lac = found.group(1)

        found = self._location_info_cellid_regex.search(output)
        if found:
            cellid = found.group(1)

        found = self._location_info_tac_regex.search(output)
        if found:
            tac = found.group(1)

        found = self._location_info_nid_regex.search(output)
        if found:
            nid = found.group(1)

        found = self._location_info_bid_regex.search(output)
        if found:
            bid = found.group(1)

        return CellularLocation(
            cell_id=cellid,
            lac=lac,
            tac=tac,
            bid=bid,
            nid=nid)

    @critical_section
    @handle_error_return_code
    def get_cellular_fw(self):
        """
        Return Cellular FW information.
        Example entry: 9999999_9902266_SWI9X15C_05.05.58.01_00_VZW_005.029_001
        """
        self.at("ATE0")
        self.at("AT!ENTERCND=\"A710\"")

        # get current fw version
        current_fw = self.at("AT+CGMR")
        _logger.debug("{}".format(current_fw))
        fw_regex = r"SWI9X15C_(.*?) r"
        fw_matches = re.finditer(fw_regex, current_fw["info"])
        for _, match in enumerate(fw_matches):
            current_fw = match.group(1)
            break

        # get all carrier profiles
        at_obj = self.at("AT!priid?", 3)
        _logger.debug(at_obj)
        if at_obj["status"] != "ok":
            return None

        regex = r"^Carrier PRI: (.*?)$"
        matches = re.finditer(regex, at_obj["info"], re.MULTILINE)
        pri_list = [
            (lambda match: match.group(1))(match)
            for _, match in enumerate(matches)
        ]

        result = {
            "switchable": True,
            "current": {},
            "preferred": {},
            "available": []
        }

        for entry in pri_list:
            entry_cols = entry.split("_")
            result["available"].append({
                # "fwver": entry_cols[3],
                "fwver": current_fw,  # FIXME: Use fixed fwver now
                "config": "_".join(entry_cols[5:8]),
                "carrier": entry_cols[5],
            })
        _logger.debug("{}".format(result))

        regex = r"^(.*?):\s+(\S*)$"
        at_obj = self.at("AT!GOBIIMPREF?")
        _logger.debug(at_obj)
        if at_obj["status"] != "ok":
            return None
        matches = re.finditer(regex, at_obj["info"], re.MULTILINE)
        status_lines = [
            (lambda match: (match.group(1), match.group(2)))(match)
            for _, match in enumerate(matches)
        ]

        for entry in status_lines:
            key = entry[0].strip()
            if key == "preferred fw version":
                # FIXME: Use fixed fwver now
                result["preferred"]["fwver"] = current_fw
            elif key == "preferred carrier name":
                result["preferred"]["carrier"] = entry[1]
            elif key == "preferred config name":
                result["preferred"]["config"] = entry[1]
            elif key == "current fw version":
                # FIXME: Use fixed fwver now
                result["current"]["fwver"] = current_fw
            elif key == "current carrier name":
                result["current"]["carrier"] = entry[1]
            elif key == "current config name":
                result["current"]["config"] = entry[1]
            else:
                pass

        return result

    @critical_section
    @handle_error_return_code
    def set_cellular_fw(self, fwver, config, carrier):
        """
        Return Cellular FW information.
        """
        atcmd = "AT!GOBIIMPREF=\"{}\",\"{}\",\"{}\"".format(
            fwver, carrier, config)
        _logger.debug("cell_mgmt ATE0")
        self.at("ATE0")
        _logger.debug("cell_mgmt AT!ENTERCND=A710")
        self.at("AT!ENTERCND=\"A710\"")
        _logger.debug("cell_mgmt {}".format(atcmd))
        self.at(atcmd)
        self.power_cycle()


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
