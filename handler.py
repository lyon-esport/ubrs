# -*- encoding: utf-8 -*-
#
# Etienne Glossi - Avril 2012 - etienne.glossi@gmail.com
# Interface web de supervision et gestion des relays de broadcast UDP pour les jeux en LANs.
# Permet de propager le broadcast entre plusieurs VLANs.

from tornado.web import RequestHandler
import config as configuration
import os

# Handler Generique
class BaseHandler(RequestHandler):
    def initialize(self, relay):
        self.relay = relay


# UDP-Broadcast-Relay Supervisor Main Page
# Le coeur du serveur (interface). Intercepte toute les requêtes de connections vers /.
# Présente l'état actuel du serveur de relay: vlan, ports relayés.
class MainPage(BaseHandler):
    # HTTP GET
    def get(self):
        self.render(os.getcwd() + "/templates/index.html",
            ports=self.relay.get_ports(),
            ifaces=self.relay.get_ifaces(),
            system_ifaces = self.relay.netifaces(),
            trunk = self.relay.trunk(),
            oam = self.relay.oam(),
            config = configuration
        )


# UDP-Brodacast-Relay Supervisor Add Port
# Ajout d'un port
class AddPortHandler(BaseHandler):
    # HTTP POST
    def get(self):
        port = int(self.get_argument("port"))
        game = self.get_argument("game")
        if self.relay.add_port(port, game):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Remove Port
# Suppression d'un port
class RemovePortHandler(BaseHandler):
    # HTTP POST
    def get(self):
        port = int(self.get_argument("port"))
        if self.relay.remove_port(port):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Stop Port
# Démarrage du relay sur le ou les ports
class StartPortHandler(BaseHandler):
    # HTTP POST
    def get(self):
        port = int(self.get_argument("port"))
        if self.relay.start_port(port):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Start Port
# Arret du relay sur le ou les ports
class StopPortHandler(BaseHandler):
    # HTTP POST
    def get(self):
        port = int(self.get_argument("port"))
        if self.relay.stop_port(port):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Add Interface
# Creation d'une interface
class AddIfHandler(BaseHandler):
    # HTTP POST
    def get(self):
        vlan = int(self.get_argument("vlan"))
        ip = self.get_argument("ip")
        mask = self.get_argument("mask")
        if self.relay.add_if(vlan, ip, mask):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Remove Interface
# Suppression d'une interface
class RemoveIfHandler(BaseHandler):
    # HTTP POST
    def get(self):
        vlan = int(self.get_argument("vlan"))
        if self.relay.remove_if(vlan):
            self.redirect('/')
        else:
            self.write('Humm :/')


# UDP-Brodacast-Relay Supervisor Set Trunk Interface
# Selection de l'interface trunk à utiliser
class SetTrunkIfHandler(BaseHandler):
    # HTTP POST
    def get(self):
        ifname = self.get_argument("ifname")
        if self.relay.set_trunk_if(ifname):
            self.redirect('/')
        else:
            self.write('Humm :/')

# UDP-Brodacast-Relay Supervisor Set Trunk Interface
# Selection de l'interface trunk à utiliser
class SetOamIfHandler(BaseHandler):
    # HTTP POST
    def get(self):
        ifname = self.get_argument("ifname")
        if self.relay.set_oam_if(ifname):
            self.redirect('/')
        else:
            self.write('Humm :/')
