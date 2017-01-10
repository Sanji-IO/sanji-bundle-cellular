"""
Helper library.
"""

from enum import Enum
import logging
from monotonic import monotonic
import sh
from sh import ErrorReturnCode, TimeoutException
import sys
from threading import Thread
from time import sleep
from traceback import format_exc

from cellular_utility.cell_mgmt import (
    CellMgmt, CellMgmtError, SimStatus, CellularLocation, Signal,
    CellularNumber
)
from cellular_utility.event import Log

_logger = logging.getLogger("sanji.cellular")


class StopException(Exception):
    pass


class CellularInformation(object):

    def __init__(
            self,
            mode=None,
            signal_csq=None,
            signal_rssi_dbm=None,
            signal_ecio_dbm=None,
            operator=None,
            lac=None,
            cell_id=None,
            number=None):

        if (not isinstance(mode, str) or
                not isinstance(signal_csq, int) or
                not isinstance(signal_rssi_dbm, int) or
                not isinstance(signal_ecio_dbm, float) or
                not isinstance(operator, str) or
                not isinstance(lac, str) or
                not isinstance(cell_id, str) or
                not isinstance(number, str)):
            raise ValueError

        if lac == "Unknown" or cell_id == "Unknown":
            _logger.warning("lac = {}, cell_id = {}".format(lac, cell_id))

        self._mode = mode
        self._signal_csq = signal_csq
        self._signal_rssi_dbm = signal_rssi_dbm
        self._signal_ecio_dbm = signal_ecio_dbm
        self._operator = operator
        self._lac = lac
        self._cell_id = cell_id
        self._number = number

    @property
    def mode(self):
        return self._mode

    @property
    def signal_csq(self):
        return self._signal_csq

    @property
    def signal_rssi_dbm(self):
        return self._signal_rssi_dbm

    @property
    def signal_ecio_dbm(self):
        return self._signal_ecio_dbm

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
    def number(self):
        return self._number

    @staticmethod
    def get():
        cell_mgmt = CellMgmt()

        try:
            signal = cell_mgmt.signal_adv()

        except CellMgmtError:
            signal = Signal(mode="n/a", rssi_dbm=0, ecio_dbm=0.0, csq=0)

        try:
            operator = cell_mgmt.operator()

        except CellMgmtError:
            operator = "n/a"

        try:
            cellular_location = cell_mgmt.get_cellular_location()

        except CellMgmtError:
            cellular_location = CellularLocation(
                lac="n/a",
                cell_id="n/a")

        try:
            number = cell_mgmt.number()

        except CellMgmtError:
            number = CellularNumber(
                number="n/a")

        return CellularInformation(
            signal.mode,
            signal.csq,
            signal.rssi_dbm,
            signal.ecio_dbm,
            operator,
            cellular_location.lac,
            cellular_location.cell_id,
            number.number)


class CellularObserver(object):
    def __init__(
            self,
            period_sec):
        self._period_sec = period_sec

        self._cell_mgmt = CellMgmt()

        self._stop = True
        self._thread = None

        self._cellular_information = None

    def cellular_information(self):
        return self._cellular_information

    def start(self):
        self._stop = False

        self._thread = Thread(target=self._main_thread)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()

    def _main_thread(self):
        next_check = monotonic()
        while not self._stop:

            now = monotonic()
            if now < next_check:
                sleep(1)
                continue

            next_check = now + self._period_sec

            try:
                cellular_information = CellularInformation.get()
                if cellular_information is not None:
                    self._cellular_information = cellular_information
            except Exception as e:
                _logger.error("should not reach here")
                _logger.warning(e)


class CellularLogger(object):
    def __init__(
            self,
            period_sec):
        self._period_sec = period_sec

        self._stop = True
        self._thread = None

        self._mgr = None
        self._log = Log()

    def start(
            self,
            manager):
        self._mgr = manager

        self._stop = False

        self._thread = Thread(target=self._main_thread)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()

        self._mgr = None

    def _main_thread(self):
        next_check = monotonic()
        while not self._stop:

            now = monotonic()
            if now < next_check:
                sleep(1)
                continue

            next_check = now + self._period_sec

            try:
                cinfo = self._mgr.cellular_information()
                if cinfo is not None:
                    self._log.log_cellular_information(cinfo)
                else:
                    next_check = now + 10
            except Exception as e:
                _logger.error("should not reach here")
                _logger.warning(e)


class Manager(object):
    PING_REQUEST_COUNT = 3
    PING_TIMEOUT_SEC = 20

    class Status(Enum):
        initializing = 0
        nosim = 1
        pin = 2
        ready = 3
        connecting = 4
        connect_failure = 5
        connected = 6
        power_cycle = 7
        service_searching = 8
        service_attached = 9

    class StaticInformation(object):
        def __init__(
                self,
                pin_retry_remain=None,
                icc_id=None,
                imei=None):

            if (not isinstance(pin_retry_remain, int) or
                    not isinstance(icc_id, str) or
                    not isinstance(imei, str)):
                raise ValueError

            self._pin_retry_remain = pin_retry_remain
            self._icc_id = icc_id
            self._imei = imei

        @property
        def pin_retry_remain(self):
            return self._pin_retry_remain

        @property
        def icc_id(self):
            return self._icc_id

        @property
        def imei(self):
            return self._imei

    def __init__(
            self,
            dev_name=None,
            enabled=None,
            pin=None,
            pdp_context_static=None,
            pdp_context_id=None,
            pdp_context_primary_apn=None,
            pdp_context_primary_type=None,
            pdp_context_secondary_apn=None,
            pdp_context_secondary_type=None,
            pdp_context_retry_timeout=None,
            keepalive_enabled=None,
            keepalive_host=None,
            keepalive_period_sec=None,
            log_period_sec=None):

        if (not isinstance(dev_name, str) or
                not isinstance(enabled, bool) or
                not isinstance(pdp_context_static, bool) or
                not isinstance(pdp_context_id, int) or
                not (isinstance(pdp_context_primary_apn, str) or
                     isinstance(pdp_context_primary_apn, unicode) or
                     pdp_context_primary_apn is None) or
                not (isinstance(pdp_context_primary_type, str) or
                     pdp_context_primary_type is None) or
                not (isinstance(pdp_context_secondary_apn, str) or
                     isinstance(pdp_context_secondary_apn, unicode) or
                     pdp_context_secondary_apn is None) or
                not (isinstance(pdp_context_secondary_type, str) or
                     pdp_context_secondary_type is None) or
                not isinstance(pdp_context_retry_timeout, int) or
                not isinstance(keepalive_enabled, bool) or
                not isinstance(keepalive_host, str) or
                not isinstance(keepalive_period_sec, int) or
                not isinstance(log_period_sec, int)):
            raise ValueError

        if pin is not None:
            if not isinstance(pin, str) or len(pin) != 4:
                raise ValueError

        self._dev_name = dev_name
        self._enabled = enabled
        self._pin = pin
        self._pdp_context_static = pdp_context_static
        self._pdp_context_id = pdp_context_id
        self._pdp_context_primary_apn = pdp_context_primary_apn
        self._pdp_context_primary_type = pdp_context_primary_type
        self._pdp_context_secondary_apn = pdp_context_secondary_apn
        self._pdp_context_secondary_type = pdp_context_secondary_type
        self._pdp_context_retry_timeout = pdp_context_retry_timeout
        self._keepalive_enabled = keepalive_enabled
        self._keepalive_host = keepalive_host
        self._keepalive_period_sec = keepalive_period_sec
        self._log_period_sec = log_period_sec

        self._status = Manager.Status.initializing

        self._static_information = None

        self._cell_mgmt = CellMgmt()
        self._stop = True

        self._thread = None

        self._cellular_logger = None
        self._observer = None

        # instance of CellularInformation
        self._cellular_information = None

        # instance of NetworkInformation
        self._network_information = None

        self._update_network_information_callback = None

        self._log = Log()

        # verify SIM card at very beginning
        self.verify_sim()

    def set_update_network_information_callback(
            self,
            callback):
        self._update_network_information_callback = callback

    def status(self):
        return self._status

    def static_information(self):
        return self._static_information

    def cellular_information(self):
        """Return an instance of CellularInformation or None."""
        if self._observer is not None:
            cinfo = self._observer.cellular_information()
            if cinfo is not None:
                self._cellular_information = cinfo

        return self._cellular_information

    def network_information(self):
        """Return an instance of NetworkInformation or None."""
        return self._network_information

    def pdp_context_list(self):
        """Return a list of PDP context."""
        return self._cell_mgmt.pdp_context_list()

    def verify_sim(self):
        sim_status = self._cell_mgmt.sim_status()
        _logger.debug("sim_status = " + sim_status.name)

        if sim_status == SimStatus.nosim:
            self._status = Manager.Status.nosim
            return sim_status

        if sim_status == SimStatus.pin:
            if self._pin is None:
                self._status = Manager.Status.pin
                self._log.log_event_no_pin()
                return sim_status

            # set pin
            try:
                self._cell_mgmt.set_pin(self._pin)
                self._sleep(3, critical_section=True)
                sim_status = self._cell_mgmt.sim_status()
                if sim_status == SimStatus.ready:
                    self._status = Manager.Status.ready
                    return sim_status

            except CellMgmtError:
                _logger.warning(format_exc())
                self._pin = None
                self._log.log_event_pin_error()

        if sim_status == SimStatus.ready:
            self._status = Manager.Status.ready

        return sim_status

    def start(self):
        self._stop = False

        self._thread = Thread(target=self._main_thread)
        self._thread.daemon = True
        self._thread.start()

        self._cellular_logger = CellularLogger(self._log_period_sec)
        self._cellular_logger.start(self)

    def stop(self):
        self._stop = True
        self._thread.join()

        self._cellular_logger.stop()

    def _main_thread(self):
        while True:
            try:
                self._loop()

            except StopException:
                if self._observer is not None:
                    self._observer.stop()
                    self._observer = None

                self._log.log_event_cellular_disconnect()
                self._cell_mgmt.stop()
                break

            except Exception:
                _logger.error("should not reach here")
                _logger.warning(format_exc())
                self._power_cycle(force=True)

    def _loop(self):
        try:
            if not self._initialize():
                if self._enabled:
                    self._power_cycle()

                return

            # start observation
            self._observer = CellularObserver(period_sec=30)
            self._observer.start()

            if self._enabled:
                self._operate()
            else:
                while True:
                    self._sleep(60)

            # stop observation
            self._observer.stop()
            self._observer = None

            self._power_cycle()

        except CellMgmtError:
            _logger.warning(format_exc())
            self._power_cycle()

    def _interrupt_point(self):
        if self._stop:
            raise StopException

    def _initialize(self):
        """Return True on success, False on failure."""
        self._status = Manager.Status.initializing
        self._static_information = None
        self._cellular_information = None
        self._network_information = None

        retry = 0
        max_retry = 10
        while retry < max_retry:
            self._interrupt_point()

            self._status = Manager.Status.initializing

            sim_status = self.verify_sim()
            if sim_status == SimStatus.nosim:
                self._sleep(10)
                retry += 1
                continue

            self._initialize_static_information()
            self._cellular_information = CellularInformation.get()

            if sim_status != SimStatus.ready:
                raise StopException

            self._status = Manager.Status.ready
            return True

        sim_status = self._cell_mgmt.sim_status()
        if sim_status == SimStatus.nosim:
            self._log.log_event_nosim()

        return False

    def _initialize_static_information(self):
        _logger.debug("_initialize_static_information")
        while True:
            try:
                pin_retry_remain = self._cell_mgmt.get_pin_retry_remain()
                minfo = self._cell_mgmt.m_info()

                self._static_information = Manager.StaticInformation(
                    pin_retry_remain=pin_retry_remain,
                    icc_id=minfo.icc_id,
                    imei=minfo.imei)

                break

            except CellMgmtError:
                _logger.warning(format_exc())
                self._sleep(10)
                continue

    def _operate(self):
        while True:
            self._interrupt_point()

            self._status = Manager.Status.connecting

            if not self._try_connect(self._pdp_context_primary_apn,
                                     self._pdp_context_primary_type,
                                     self._pdp_context_retry_timeout):

                if self._pdp_context_static is False or \
                        self._pdp_context_secondary_apn is None or \
                        self._pdp_context_secondary_apn == "":
                    break

                if not self._try_connect(self._pdp_context_secondary_apn,
                                         self._pdp_context_secondary_type,
                                         self._pdp_context_retry_timeout):
                    break

            self._status = Manager.Status.connected

            while True:
                self._interrupt_point()

                connected = self._cell_mgmt.status()
                if not connected:
                    self._log.log_event_cellular_disconnect()
                    break

                if self._keepalive_enabled:
                    if not self._checkalive_ping():
                        self._log.log_event_checkalive_failure()
                        break

                self._sleep(
                    self._keepalive_period_sec
                    if self._keepalive_enabled
                    else 60)

    def _attach(self):
        """Return True on success, False on failure.
        """
        _logger.debug("check if module attached with service")

        retry = 0
        while True:
            if self._status == Manager.Status.power_cycle:
                self._sleep(1)
                continue

            self._status = Manager.Status.service_searching

            if not self._cell_mgmt.attach():
                retry += 1
                if retry > 180:
                    return False
                self._sleep(1)
                continue
            break

        self._status = Manager.Status.service_attached
        return True

    def _try_connect(self, pdpc_apn, pdpc_type, retry_timeout):
        retry = monotonic() + retry_timeout
        while True:
            self._interrupt_point()

            self._status = Manager.Status.connecting
            if not self._connect(pdpc_apn, pdpc_type):
                self._status = Manager.Status.connect_failure

                if monotonic() >= retry:
                    break

                self._sleep(10)
            else:
                return True

    def _connect(self, pdpc_apn, pdpc_type):
        """Return True on success, False on failure.
        """
        self._network_information = None

        try:
            self._log.log_event_connect_begin()

            self._cell_mgmt.stop()

            try:
                if self._pdp_context_static is True:
                    self._cell_mgmt.set_pdp_context(
                        self._pdp_context_id, pdpc_apn, pdpc_type)
                    if self.verify_sim() != SimStatus.ready:
                        raise StopException

                pdpc = (item for item in self.pdp_context_list()
                        if item["id"] == self._pdp_context_id).next()
                apn = pdpc["apn"]
            except:
                self._log.log_event_no_pdp_context()
                return False
            if apn == "":
                self._log.log_event_no_apn()
                return False

            # try to attach before connect
            if not self._attach():
                return False

            nwk_info = self._cell_mgmt.start(apn=apn)

            self._log.log_event_connect_success(nwk_info)

            connected = self._cell_mgmt.status()
            if not connected:
                self._log.log_event_cellular_disconnect()
                return False

        except CellMgmtError:
            _logger.warning(format_exc())

            self._log.log_event_connect_failure()
            return False

        if self._keepalive_enabled:
            if not self._checkalive_ping():
                self._log.log_event_checkalive_failure()
                return False

        self._network_information = nwk_info
        # update nwk_info
        if self._update_network_information_callback is not None:
            self._update_network_information_callback(nwk_info)

        return True

    def _power_cycle(self, force=False):
        try:
            self._log.log_event_power_cycle()
            self._status = Manager.Status.power_cycle

            self._cell_mgmt.power_cycle(force, timeout_sec=60)
        except CellMgmtError:
            _logger.warning(format_exc())

    def _sleep(self, sec, critical_section=False):
        until = monotonic() + sec

        while monotonic() < until:
            if not critical_section:
                self._interrupt_point()
            sleep(1)

    def _checkalive_ping(self):
        """Return True on ping success, False on failure."""
        for _ in xrange(0, self.PING_REQUEST_COUNT):
            try:
                sh.ping(
                    "-c", "1",
                    "-I", self._dev_name,
                    "-W", str(self.PING_TIMEOUT_SEC),
                    self._keepalive_host,
                    _timeout=self.PING_TIMEOUT_SEC + 5
                )

                return True
            except (ErrorReturnCode, TimeoutException):
                _logger.warning(format_exc())

                continue

        return False


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("sh").setLevel(logging.INFO)

    mgr = Manager(
        dev_name="wwan0",
        enabled=True,
        pin="0000",
        apn="internet",
        keepalive_enabled=True,
        keepalive_host="8.8.8.8",
        keepalive_period_sec=60)

    mgr.start()
    sleep(600)
    mgr.stop()
