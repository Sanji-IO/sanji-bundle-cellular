"""
Export cellular event to log file.
"""

from time import gmtime, strftime


class Log(object):
    LOGFILE_PATH = "/var/log/cellular.log"
    TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self):
        self._log_file = open(self.LOGFILE_PATH, "a")

    def log_nosim(self):
        """
        As title.
        """
        self._log("no sim card")

    def log_cellular_information(
            self,
            cellular_information):
        """
        ci should be an instance of
          cellular_utility.management.CellularInformation
        """
        self._log(
            "signal " + str(cellular_information.signal) + " dBm"
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

    def log_event_power_cycle(self):
        """
        Power cycle cellular module.
        """
        self._log("power-cycle")

    def _log(self, msg):
        """
        Do actual logging.
        """
        self._log_file.write(
            strftime(self.TIME_FORMAT, gmtime())
            + ": " + msg + '\n')

        self._log_file.flush()
