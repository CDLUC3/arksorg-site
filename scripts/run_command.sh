#!/bin/bash
source venv/bin/activate
export RSLV_DB_CONNECTION_STRING="sqlite:////apps/ezid/var/data/pid_config.sqlite"
python3 $@
