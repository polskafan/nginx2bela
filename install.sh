#!/bin/bash

BASE_DIRECTORY=$(pwd)

# Install Python environment
python3.7 -m venv venv
venv/bin/pip install -r dependencies.txt
venv/bin/pip install -r requirements.txt

# Create a local instance of belacoder and srtla
ln -s /usr/bin/belacoder $BASE_DIRECTORY/belacoder_push
ln -s /usr/bin/srtla_send $BASE_DIRECTORY/srtla_send_push

# Install Autostart Script
sed "s|###BASE_DIRECTORY###|$BASE_DIRECTORY|g" systemd/nginx2bela.service > /tmp/nginx2bela.service
sudo cp /tmp/nginx2bela.service /etc/systemd/system/nginx2bela.service
rm /tmp/nginx2bela.service

# Reload systemctl daemons files
sudo systemctl daemon-reload

# Start Services
sudo systemctl restart nginx2bela

# Enable Autostart Scripts
sudo systemctl enable nginx2bela