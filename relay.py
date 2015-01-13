#!/usr/bin/env python2.6
# -*- encoding: utf-8 -*-
#
# Etienne Glossi - Avril 2012 - etienne.glossi@gmail.com
# Interface web de supervision et gestion des relays de broadcast UDP pour les jeux en LANs.
# Permet de propager le broadcast entre plusieurs VLANs.

import os
import config
import subprocess
import netifaces
from time import sleep

# Relay
# Interface avec le programme "udp-broadcast-relay". Gère les ports et interfaces en écoute.
class Relay:
    def __init__(self, path):
        self.path = path
        self.ports = dict()
        self.ifaces = dict()

    def add_port(self, port, game):
        """ Ajout d'un port et se met a le relayer sur toute les interfaces. """
        if port in self.ports:
            return False
        self.ports[port] = Port(port, game)
        return self.start_port(port)

    def remove_port(self, port):
        """ Suppression d'un port de la liste. """
        if port not in self.ports:
            return False
        del self.ports[port]
        return True

    def stop_port(self, port):
        """ Arrete de relayer un port sur toutes les interfaces. """
        if port == 0: #tous
            return [p for p in self.ports if not self.ports[p].stop()]
        if port in self.ports :
            return self.ports[port].stop()
        return False

    def start_port(self, port):
        """ Relay un port sur toutes les interfaces. """
        if port == 0: #tous
            return [p for p in self.ports if not self.ports[p].start(self)]
        if port in self.ports :
            return self.ports[port].start(self)
        return False

    def restart_port(self, port):
        """ Relay un port sur toutes les interfaces. """
        if port == 0: #tous
            return [p for p in self.ports if not self.ports[p].restart(self)]
        if port in self.ports :
            return self.ports[port].restart(self)
        return False

    def check_unrelayed_ports(self):
        """ Verifie que tous les ports listés sont bien relayés. """
        return [p for p in self.ports if not p.is_relayed()]

    def get_ports(self):
        return self.ports.values()

    def restart_ports(self):
        return self.restart_port(0)

    def start_ports(self):
        return self.start_port(0)

    def stop_ports(self):
        return self.stop_port(0)

    def add_if(self, vlan, ip = None, mask = None):
        """ Ajoute et créé l'interface du VLAN (une seule if/vlan) """
        if vlan in self.ifaces:
            return False
        self.ifaces[vlan] = Interface(vlan, ip, mask)
        self.restart_ports()
        return True

    def remove_if(self, vlan):
        """ Supprime l'interface du VLAN. """
        if vlan not in self.ifaces:
            return False
        self.stop_ports()
        del self.ifaces[vlan]
        self.start_ports()
        return True

    def set_trunk_if(self, ifname):
        """ Définie l'interface trunk à utiliser. """
        return Interface.set_trunk(ifname)

    def set_oam_if(self, ifname):
        """ Définie l'interface d'administration à utiliser. """
        return Interface.set_oam(ifname)

    def check_unrelayed_ifaces(self):
        """ Verifie que tous les ports sont bien relayés par toutes les interfaces. """
        i = {}
        for p in self.ports:
            if p.is_relayed():
                i[p] = filter(lambda x:x not in p.relayed_ifaces(), self.get_ifaces())
        return i

    def get_ifaces(self):
        return self.ifaces.values()

    @staticmethod
    def netifaces():
        return dict((i, netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr']) for i in netifaces.interfaces() if '.' not in i)

    @staticmethod
    def trunk():
        return Interface.get_trunk()

    @staticmethod
    def oam():
        return Interface.get_oam()


# Port
# Stocke les informations de numero de port avec le processus associé lorsque le daemon est en écoute.
class Port:
    _ubrid = 0
    def __init__(self, port, game):
        self.port = port
        self.game = game
        self._proc = None
        self._ifaces = None
        self.__id = Port._ubrid = Port._ubrid + 1

    def __del__(self):
        self.stop()

    def __str__(self):
        return "%d (%s)" % (self.port, self.game)

    def _reset(self):
        self._proc = None
        self._ifaces = None
        return True

    def is_relayed(self):
        """ Détermine si le port est actuellement relayé sur/par les différentes interfaces/vlan. """
        return (self._proc != None and self._proc.poll() == None) or not self._reset()

    def relayed_ifaces(self):
        """ Retourne le nom des interfaces qui relay le port. """
        if self.is_relayed():
            return self._ifaces
        return None

    def pid(self):
        return self._proc.pid

    def start(self, relay):
        """ Lance le broadcast-relay sur le port. """
        # TODO: ajouter redirection stderr
        if relay == None or relay.ifaces == {}:
            return False
        if not self.is_relayed():
            self._ifaces = relay.get_ifaces()
            print [relay.path, str(self.__id), str(self.port), str(relay.oam())] + [i.name for i in self._ifaces]
            self._proc = subprocess.Popen([relay.path, str(self.__id), str(self.port), str(relay.oam())] + [i.name for i in self._ifaces])
            print "lancee sur", ','.join([i.name for i in self._ifaces] + [relay.oam()])
            sleep(1) #afin d'etre sur qu'il s'est lancé
        return self.is_relayed()

    def stop(self):
        """ Arrête le broadcast-relay sur le port. """
        if self.is_relayed():
            self._proc.terminate()
        print "stop", self
        sleep(1) #afin d'etre sur qu'il s'est arreté
        return not self.is_relayed()

    def restart(self, relay):
        """ Relance le relay sur le port. Utile en cas d'ajout d'une interface. """
        if self.stop():
            return self.start(relay)
        return False


# Interface
# Stocke les informations des interfaces utilisées par le relay
class Interface:
    # interface physique en mode trunk a utiliser
    _trunk_if = None
    # interface physique OAM
    _oam_if = None
    def __init__(self, vlan, ip = None, mask = None, name = ""):
        if Interface._oam_if == None and vlan != config.OAM_VLAN and vlan != 0:
            raise ReferenceError("L'interface oam n'a pas été définie avec Interface.set_oam(<ifname>).")
        elif Interface._oam_if != None and vlan == config.OAM_VLAN:
            raise SystemError("Impossible de créer une interface virtuelle sur le vlan d'administration !")
        elif Interface._trunk_if == None and vlan != config.OAM_VLAN and vlan != 0:
            raise ReferenceError("L'interface trunk n'a pas été définie avec Interface.set_trunk(<ifname>).")

        self.vlan = vlan
        self.ip = ip if ip else config.DEFAULT_VLAN_IP % vlan
        self.mask = mask if mask else config.DEFAULT_VLAN_MASK
        self.name = name
        if not self.__initialize():
            raise SystemError("Impossible de creer l'interface %s (VLAN %d): %s / %s" % (self.name, self.vlan, self.ip, self.mask))

    def __del__(self):
        """ Supprimer l'interface. """
        print "del", self
        if self.vlan > 0:
            p = subprocess.Popen(["vconfig", "rem", self.name])

    def __str__(self):
        return "%s (%s/%d)" % (self.name, self.ip, Interface.mask_len(self.mask))

    def __initialize(self):
        """ Créer l'interface """
        if (self.vlan == 0 or self.vlan == config.OAM_VLAN):
            sys_if = Relay.netifaces()
            if not self.name in sys_if:
                return False
            # interface trunk or oam
            self.ip = sys_if[self.name]
            self.mask = "0.0.0.0"
        else :
            self.name = Interface._trunk_if.name + ".%d" % (self.vlan)
            # creation de l'interface
            p = subprocess.Popen(["vconfig", "add", Interface._trunk_if.name, "%d" % self.vlan])
            if p.wait() != 0:
                return False
            p = subprocess.Popen(["ifconfig", self.name, self.ip, "netmask", self.mask, "up"])
            if p.wait() != 0:
                return False
        return True

    @staticmethod
    def mask_len(mask):
        """ Calcule la taille d'un masque réseau passé au format X.X.X.X """
        mask = mask.split('.')
        if len(mask) != 4:
            return "Mauvais format de masque !"
        return str(bin(int(mask[0])) + bin(int(mask[1])) + bin(int(mask[2])) + bin(int(mask[3]))).count('1')

    @staticmethod
    def set_trunk(iface):
        Interface._trunk_if = Interface(0, name = iface)
        return True

    @staticmethod
    def get_trunk():
        return "" if not Interface._trunk_if else Interface._trunk_if.name

    @staticmethod
    def set_oam(iface):
        Interface._oam_if = Interface(config.OAM_VLAN, name = iface)
        return True

    @staticmethod
    def get_oam():
        return "" if not Interface._oam_if else Interface._oam_if.name
