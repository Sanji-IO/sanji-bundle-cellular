"""
Export cellular event to log file.
"""

import logging

_logger = logging.getLogger("sanji.cellular_utility.event")


class Log(object):
    def __init__(self):
        pass

    def log_event_nosim(self):
        """
        As title.
        """
        self._log("no sim card")

    def _rssi_from_dbm(self, signal):
        """
        Convert RSSI value from signal dBm value
        """
        if signal == 0:
            return 0

        if signal < -110:
            return 0

        return int(0.5 * (signal + 109) + 2)

    def log_cellular_information(
            self,
            cellular_information):
        """
        ci should be an instance of
          cellular_utility.management.CellularInformation
        """
        self._log(
            "mode " + cellular_information.mode
            + ", signal " + str(cellular_information.signal) + " dBm"
            + ", rssi " + str(self._rssi_from_dbm(cellular_information.signal))
            + ", lac " + cellular_information.lac
            + ", cell_id " + cellular_information.cell_id)

    def log_event_connect_begin(self):
        """
        Connect begin.
        """
        self._log("connect-begin")

    def log_event_connect_success(
            self,
            network_information):
        """
        Connect success.
        network_information should be an instance of
          cellular_utility.management.NetworkInformation
        """
        self._log(
            "connect-success"
            + ", ip = " + network_information.ip
            + ", netmask = " + network_information.netmask
            + ", gateway = " + network_information.gateway
            + ", dns = " + str(network_information.dns_list))

    def log_event_connect_failure(self):
        """
        Connect failure.
        """
        self._log("connect-failure")

    def log_event_cellular_disconnect(self):
        """
        Cellular disconnect.
        """
        self._log("cellular-disconnect")

    def log_event_checkalive_failure(self):
        """
        Checkalive failure.
        """
        self._log("checkalive-failure")

    def log_event_pin_error(self):
        """
        PIN error.
        """
        self._log("pin-error, switched SIM card?")

    def log_event_power_cycle(self):
        """
        Power cycle cellular module.
        """
        self._log("power-cycle")

    def _log(self, msg):
        """
        Do actual logging.
        """
        _logger.info("cellular-event: " + msg)
