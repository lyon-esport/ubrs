#!/usr/bin/python

PORT = [9100, 29900, 14001, 61012, 27015, 28960, 2350]

param = ""
for i in range(10,31):
	print "vconfig add eth1 %d" % i
	print "ifconfig eth1.%d 172.16.%d.254/24" % (i,i)
	param += "eth1.%d " % i	

for p in PORT:
	print "./udp-broadcast-relay -f 1 %d %s eth0" % (p,param) 
