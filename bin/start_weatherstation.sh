#!/bin/bash

location=`cat $HOME/.weatherstation_location`
station=`cat $HOME/.weatherstation_name`

unset CLIENT_ID CLIENT_SECRET REFRESH_TOKEN
set -x
python $location/weatherStation/weatherStation.py $station
