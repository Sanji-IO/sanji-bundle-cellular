#!/bin/sh

/usr/lib/libqmi/qmi-proxy &

qmicli $@
