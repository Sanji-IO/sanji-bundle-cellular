"""
Helper library.
"""

from enum import Enum
import logging
from monotonic import monotonic
import sh
from sh import ErrorReturnCode
import sys
from threading import Thread
from time import sleep
from traceback import format_exc

from cellular_utility.cell_mgmt import CellMgmt, CellMgmtError, SimStatus
from cellular_utility.event import Log

_logger = logging.getLogger("sanji.cellular")


class StopException(Exception):
    pass


class CellularInformation(object):

    def __init__(
            self,
            mode=None,
            signal_dbm=None,
            operator=None,
            lac=None,
            cell_id=None):

        if (not isinstance(mode, str) or
                not isinstance(signal_dbm, int) or
                not isinstance(operator, str) or
                not isinstance(lac, str) or
                not isinstance(cell_id, str)):
            raise ValueError

        self._mode = mode
        self._signal_dbm = signal_dbm
        self._operator = operator
        self._lac = lac
        self._cell_id = cell_id

    @property
    def mode(self):
        return self._mode

    @property
    def signal_dbm(self):
        return self._signal_dbm

    @property
    def operator(self):
        return self._operator

    @property
    def lac(self):
        return self._lac

    @property
    def cell_id(self):
        return self._cell_id

    @staticmethod
    def get():
        cell_mgmt = CellMgmt()

        try:
            signal = cell_mgmt.signal()

            operator = cell_mgmt.operator()

            m_info = cell_mgmt.m_info()

            return CellularInformation(
                signal.mode,
                signal.rssi_dbm,
                operator,
                m_info.lac,
                m_info.cell_id)

        except CellMgmtError:
            _logger.warning(format_exc())
            return None


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

            cellular_information = CellularInformation.get()

            if cellular_information is not None:
                self._cellular_information = cellular_information


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

            cinfo = self._mgr.cellular_information()
            if cinfo is not None:
                self._log.log_cellular_information(cinfo)
            else:
                next_check = now + 10


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
            apn=None,
            keepalive_enabled=None,
            keepalive_host=None,
            keepalive_period_sec=None,
            log_period_sec=None):

        if (not isinstance(dev_name, str) or
                not isinstance(enabled, bool) or
                not isinstance(apn, str) or
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
        self._apn = apn
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
        try:
            while True:
                self._loop()

        except StopException:
            if self._observer is not None:
                self._observer.stop()
                self._observer = None

            self._log.log_event_cellular_disconnect()
            self._cell_mgmt.stop()

    def _loop(self):
        try:
            if not self._initialize():
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

            sim_status = self._cell_mgmt.sim_status()
            _logger.debug("sim_status = " + sim_status.name)

            if sim_status == SimStatus.nosim:
                self._status = Manager.Status.nosim
                self._sleep(10)
                retry += 1
                continue

            if sim_status == SimStatus.pin:
                if self._pin is None:
                    self._status = Manager.Status.pin
                    self._sleep(10)
                    retry += max_retry
                    continue

                # set pin
                try:
                    self._cell_mgmt.set_pin(self._pin)
                    self._sleep(3)
                    continue

                except CellMgmtError:
                    _logger.warning(format_exc())

                    self._log.log_event_pin_error()
                    self._pin = None
                    retry += max_retry
                    continue

            assert sim_status == SimStatus.ready

            try:
                pin_retry_remain = self._cell_mgmt.get_pin_retry_remain()
                minfo = self._cell_mgmt.m_info()

                self._static_information = Manager.StaticInformation(
                    pin_retry_remain=pin_retry_remain,
                    icc_id=minfo.icc_id,
                    imei=minfo.imei)

            except CellMgmtError:
                self._sleep(10)
                retry += 1
                continue

            while self._cellular_information is None:
                self._cellular_information = CellularInformation.get()

            self._status = Manager.Status.ready
            return True

        sim_status = self._cell_mgmt.sim_status()
        if sim_status == SimStatus.nosim:
            self._log.log_event_nosim()

        return False

    def _operate(self):
        retry = 0
        while True:
            self._interrupt_point()

            self._status = Manager.Status.connecting

            if not self._connect():
                self._status = Manager.Status.connect_failure

                retry += 1

                if retry > 3:
                    break

                self._sleep(10)
                continue

            self._status = Manager.Status.connected
            retry = 0

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

    def _connect(self):
        """Return True on success, False on failure.
        """
        self._network_information = None

        try:
            self._log.log_event_connect_begin()

            self._cell_mgmt.stop()
            nwk_info = self._cell_mgmt.start(apn=self._apn)

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

    def _power_cycle(self):
        try:
            self._log.log_event_power_cycle()
            self._status = Manager.Status.power_cycle

            self._cell_mgmt.power_off()
            self._sleep(1)
            self._cell_mgmt.power_on(timeout_sec=60)

        except CellMgmtError:
            _logger.warning(format_exc())

    def _sleep(self, sec):
        until = monotonic() + sec

        while monotonic() < until:
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
                    self._keepalive_host)

                return True
            except ErrorReturnCode:
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
