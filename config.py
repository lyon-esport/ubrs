#!/usr/bin/env python2.6
# -*- encoding: utf-8 -*-
#
# Etienne Glossi - Avril 2012 - etienne.glossi@gmail.com
# Interface web de supervision et gestion des relays de broadcast UDP pour les jeux en LANs.
# Permet de propager le broadcast entre plusieurs VLANs.

### Fichier de configuration ###

# Debug ?
DEBUG = True

# Numero de port à utiliser pour le serveur web
HTTP_PORT = 80

# Adresse IP sur laquelle le serveur sera en écoute
#HTTP_IP = "10.31.77.254"
HTTP_IP = "172.16.2.254"

# Emplacement absolu de l'executable udb-broadcast-relay
UBR_PATH = "/opt/broadcast-relay/udp-broadcast-relay"
#UBR_PATH = "/usr/bin/true"

# Adresse IP par défaut d'une interface dans un VLAN. %d représente le numéro vlan
DEFAULT_VLAN_IP = "172.16.%d.254"

# Taille du masque par defaut pour une nouvelle interface d'un vlan
DEFAULT_VLAN_MASK = "255.255.255.0"

# VLAN for OAM
OAM_VLAN = 2
