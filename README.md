# README

Made for and by Lyon e-Sport - www.lyon-esport.fr.

## Installation
1. Install dependencies
`pip3 install -r requirements.txt`

2. Compile udp-broadcast-relay
`cd broadcast-relay/udp-broadcast-relay-0.3; make; cd -`

## Configuration

Please update the configuration file `config.py` before using. Note that it starts a
webserver on port 80 by default.

## Usage

Start it as a daemon (will be executed in background):

`sudo python3 ubrs.py start`

Use `stop` to stop it.

Start in foreground for debug:

`sudo python3 ubrs.py`

## Author
rarenlys - etienne.glossi@lyon-esport.fr
