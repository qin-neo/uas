#!/usr/bin/bash
if [ ! -n "$1" ] ;then
    echo "Need a case name. End!"
    exit 1
fi

if [ $# -gt 1 ] ;then
	echo "for i in {1..9999};do source /opt/python36_venv/bin/activate && cd /opt/uas && python uas.py $*;done"
    nohup bash -c "for i in {1..9999};do source /opt/python36_venv/bin/activate && cd /opt/uas && python uas.py $*;done" &
	sleep 1
	tail -F nohup.out	
fi
