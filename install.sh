#!/bin/bash

pkgs='python3-venv python3-pip'
install=false
for pkg in $pkgs; do
  status="$(dpkg-query -W --showformat='${db:Status-Status}' "$pkg" 2>&1)"
  if [ ! $? = 0 ] || [ ! "$status" = installed ]; then
    sudo apt install -y $pkg
  fi
done

if [[ ! -d "agvenv" ]]; then
    python3 -m venv agvenv
fi

source ./agvenv/bin/activate
status="$(pip3 show psutil 2>&1)"
if [[ $? = 1 ]]; then
    pip3 install psutil 2>&1
    if [[ ! $? = 0 ]]; then
        exit 1
    fi
fi