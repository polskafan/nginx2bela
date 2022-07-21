nginx2bela
=========

This is a small webserver running on Python 3.7 to listen on nginx on_publish and on_publish_done events. Whenever nginx receives an incoming RTMP stream it will launch srtla and belacoder for that stream.

It is designed to run separated from belaUI, i.e. it spawns and manages its own subprocesses that do not interfere with belaUI and won't get interfered by belaUI.

Install Prerequisites
-----
    sudo apt install python3.7 python3.7-dev python3-venv

Checkout and prepare environment
-----
    git clone https://github.com/polskafan/nginx2bela.git
    cd nginx2bela
    

Configuration
-----
    sudo cp nginx/60-belabox-rtmp.conf /etc/nginx/modules-available/60-belabox-rtmp.conf
    cp belacoder.env.sample belacoder.env
    cp srtla.env.sample srtla.env

Install
-----
    sudo bash install.sh
