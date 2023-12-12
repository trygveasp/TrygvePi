#!/bin/bash

location=`cat $HOME/.weatherstation_location`
cd $location
git pull

pip install lnetatmo==4.0.0 --upgrade

env

sleep 3
