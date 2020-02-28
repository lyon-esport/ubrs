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

1. Start the webserver:
    * as a daemon (will be executed in background): `sudo python3 ubrs.py start`
    * in foreground for debug/ `sudo python3 ubrs.py`

2. Connect to the web interface (see config.py)

3. Select the OAM interface use for the administration. It will be excluded from the relay.

4. Select the trunk interface that will receive UDP broadcast

5. Create as many interfaces as vlans

6. Add UDP port. Broadcast messages will be relayed on all the interfaces.

If you add a new interface, existing port will be updated dynamically to relay traffic on the new VLAN.

## Author
rarenlys - etienne.glossi@lyon-esport.fr
