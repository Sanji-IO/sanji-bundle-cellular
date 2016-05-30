import logging
import re
import sh
from sh import ErrorReturnCode
from traceback import format_exc

_logger = logging.getLogger("sanji.cellular")


class VnStatError(Exception):
    pass


class VnStat(object):
    TXRX_MAX = 9223372036854775807
    _totalrx_regex = re.compile(r"totalrx;([0-9]+)\n")
    _totalrxk_regex = re.compile(r"totalrxk;([0-9]+)\n")
    _totaltx_regex = re.compile(r"totaltx;([0-9]+)\n")
    _totaltxk_regex = re.compile(r"totaltxk;([0-9]+)\n")

    def __init__(self, interface):
        self._interface = interface

    def update(self):
        vnstat = sh.vnstat

        try:
            vnstat("-i", self._interface, "-u")

        except ErrorReturnCode:
            _logger.warning(format_exc())

            raise VnStatError

    def delete(self):
        vnstat = sh.vnstat
        service = sh.service

        try:
            service("vnstat", "stop")
            vnstat("-i", self._interface, "--delete", "--force")
            service("vnstat", "start")
        except ErrorReturnCode:
            _logger.warning(format_exc())

            raise VnStatError

    def get_usage(self):
        """
        Return dict like:
            {
                "txkbyte": 123123,
                "rxkbyte": 3002
            }
        """
        vnstat = sh.vnstat

        try:
            output = vnstat("-i", self._interface, "--dumpdb")
            output = str(output)

        except ErrorReturnCode:
            _logger.warning(format_exc())

            raise VnStatError

        match = self._totalrx_regex.search(output)
        if not match:
            _logger.warning("parse error: " + output)
            raise VnStatError

        rx_ = int(match.group(1))

        match = self._totalrxk_regex.search(output)
        if not match:
            _logger.warning("parse error: " + output)
            raise VnStatError

        rxk = int(match.group(1))

        match = self._totaltx_regex.search(output)
        if not match:
            _logger.warning("parse error: " + output)
            raise VnStatError

        tx_ = int(match.group(1))

        match = self._totaltxk_regex.search(output)
        if not match:
            _logger.warning("parse error: " + output)
            raise VnStatError

        txk = int(match.group(1))

        txrx_data = {
            "txkbyte": tx_ * 1024 + txk,
            "rxkbyte": rx_ * 1024 + rxk
        }

        if txrx_data["txkbyte"] >= VnStat.TXRX_MAX or \
           txrx_data["rxkbyte"] >= VnStat.TXRX_MAX:
            self.delete()
            _logger.warning("VnStat TxRx error tx:{}, rx:{}".format(
                txrx_data["txkbyte"], txrx_data["rxkbyte"]))
            raise VnStatError

        return txrx_data

if __name__ == "__main__":
    vns = VnStat("wwan0")
    vns.update()
    usage = vns.get_usage()
    print str(usage)
