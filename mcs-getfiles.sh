#!/bin/bash
ORIGFILE=$(readlink $0)
LOCALDIR=$(dirname $ORIGFILE)
cd $LOCALDIR
exec ./.venv/bin/python3 ./mcs-getfiles.py $@