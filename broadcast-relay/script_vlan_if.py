#!/usr/bin/python

PORT = [9100, 29900, 14001, 61012, 27015, 28960, 2350]

param = ""
for i in range(10,12):
	print "ip link add link eth2 name eth2.%d type vlan id %d" % (i,i)
	print "ip addr add 172.16.%d.254/24 broadcast 172.16.%d.255 dev eth2.%d" % (i,i,i)
        print "ip link set dev eth2.%d up" % i
	param += "eth2.%d " % i

for p in PORT:
	print "./udp-broadcast-relay -f 1 %d %s eth1" % (p,param)
