#!/bin/bash

stations="pc5709 pc5511 Konnerud Hokksund"

for station in $stations; do
  gpg --import ../data/pub/$station.pub || exit 1
  id=`gpg --show-key ../data/pub/$station.pub | head -2 | tail -1`
  [ -f ../data/$station.secret.gpg ] && mv ../data/$station.secret.gpg ../data/$station.secret.gpg.back
  gpg -e -r $id -o ../data/$station.secret.gpg ../data/raw/$station.txt || exit 1
done
