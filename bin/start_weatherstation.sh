#!/bin/bash

location=`cat $HOME/.weatherstation_location`
station=`cat $HOME/.weatherstation_name`

unset CLIENT_ID CLIENT_SECRET REFRESH_TOKEN
set -x
if [ $station == "Konnerud" -o $station == "Hokksund" ]; then
  crontab $location/data/crontab.$station
fi
python $location/weatherStation/weatherStation.py $station
