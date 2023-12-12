#!/bin/bash

set -x
location=`cat $HOME/.weatherstation_location`
station=`cat $HOME/.weatherstation_name`

cred="$HOME/.netatmo.credentials.copy"
gpg --import $location/data/pub/trygveasp-gpg.pub || exit 1
gpg -d -o $cred $location/data/$station.secret.gpg || exit 1

sleep 3
