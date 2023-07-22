#!/usr/bin/bash

pip install lnetatmo==3.0.0 --upgrade

env

[ -f ~/.netatmo.credentials ] && mv ~/.netatmo.credentials ~/.netatmo.credentials.old
cat ~/.netatmo.credentials.old
