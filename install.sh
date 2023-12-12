#!/bin/bash

if [ "$#" -ne "1" ]; then
  echo "Usage: $0 name"
  exit 1
fi
station=$1

echo $PWD > $HOME/.weatherstation_location
echo $station > $HOME/.weatherstation_name
# Update data
ln -sf $PWD/bin/data_weatherstation.sh $HOME/Desktop/data_weatherstation.sh

# Update source code
ln -sf $PWD/bin/update_weatherstation.sh $HOME/Desktop/update_weatherstation.sh

# Start weather station
ln -sf $PWD/bin/start_weatherstation.sh $HOME/Desktop/start_weatherstation.sh

