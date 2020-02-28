#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#
# Etienne Glossi - Avril 2012 - etienne.glossi@gmail.com
# Interface web de supervision et gestion des relays de broadcast UDP pour les jeux en LANs.
# Permet de propager le broadcast entre plusieurs VLANs.

import tornado.ioloop
import sys
import os, os.path
import handler
import config
from os import environ
from daemon import Daemon
from relay import Relay
from tornado.web import URLSpec, Application

# UDP-Brodcast-Relay Supervisor Daemon
# Lancement de l'interface de gestion web basée sur Tornado
class UBRSWebDaemon(Daemon):
    def __init__(self):
        Daemon.__init__(self, 'ubrs.pid')
        self.ip = config.HTTP_IP
        self.port = config.HTTP_PORT
        self.relay = Relay(os.path.join(os.getcwd(), config.UBR_PATH))
        self.app = UBRSApplication(self.relay)

    # methode principale, appele par start()
    # lance l'interface web tornado
    def run(self):
        self.app.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

    # on arrete proprement le serveur
    def stop(self):
        tornado.ioloop.IOLoop.instance().stop()
        self.relay.stop_and_clean()
        Daemon.stop(self)


# UDP-Broadcast-Relay Application
# Definit les différentes pages de l'interface et y associe leur handler
class UBRSApplication(Application):
    def __init__(self, relay):
        handlers = [
            (r"/",            handler.MainPage,          dict(relay=relay)),
            (r"/if/settrunk", handler.SetTrunkIfHandler, dict(relay=relay)),
            (r"/if/setoam",   handler.SetOamIfHandler,   dict(relay=relay)),
            (r"/port/add",    handler.AddPortHandler,    dict(relay=relay)),
            (r"/port/remove", handler.RemovePortHandler, dict(relay=relay)),
            (r"/port/start",  handler.StartPortHandler,  dict(relay=relay)),
            (r"/port/stop",   handler.StopPortHandler,   dict(relay=relay)),
            #(r"/port/status", handler.StatusPortHandler, dict(relay=relay)),
            (r"/if/add",      handler.AddIfHandler,      dict(relay=relay)),
            (r"/if/remove",   handler.RemoveIfHandler,   dict(relay=relay)),
        ]
        settings = dict(
            template_path=os.path.join(os.getcwd(), "templates"),
            static_path=os.path.join(os.getcwd(), "static"),
            autoescape="xhtml_escape",
            debug=config.DEBUG,
        )
        Application.__init__(self, handlers, **settings)


#### Main ####
if __name__ == "__main__":
    if environ['USER'] != "root" and environ['UID'] != "0":
        print("Uniquement root peut lancer le serveur !")
        exit(1)

    ubr = UBRSWebDaemon()
    # Background start
    action = ""
    if len(sys.argv) == 2:
        action = sys.argv[1]
    if action == "restart":
        ubr.restart()
    elif action == "stop":
        ubr.stop()
    elif action == "start":
        ubr.start()
    elif action != "":
        print("Commande inconnue %s ! Uniquement 'start', 'restart' et 'stop' sont acceptés." % action)

    # Foreground start
    if not ubr.isrunning():
        print("Demarrage en mode normal...")
        try:
            ubr.run()
        except KeyboardInterrupt:
            ubr.stop()
            print("stopping !")
    else:
        print("Déjà en cours d'execution (pid: %d)..." % ubr.isrunning())
