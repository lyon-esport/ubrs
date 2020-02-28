/*
******************************************************************
udp-broadcast-relay
	Relays UDP broadcasts to other networks, forging
	the sender address.

Copyright (c) 2003 Joachim Breitner <mail@joachim-breitner.de>

Based upon:
udp_broadcast_fw ; Forwards UDP broadcast packets to all local
	interfaces as though they originated from sender

Copyright (C) 2002  Nathan O'Sullivan

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
******************************************************************

Thanks:

Arny <cs6171@scitsc.wlv.ac.uk>
- public domain UDP spoofing code
http://www.netfor2.com/ip.htm
- IP/UDP packet formatting info

*/

#define MAXIFS	256
#define DPRINT  if (debug) printf
#define IPHEADER_LEN 20
#define UDPHEADER_LEN 8
#define HEADER_LEN (IPHEADER_LEN + UDPHEADER_LEN)
#define TTL_ID_OFFSET 64

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in_systm.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <errno.h>
#include <string.h>
#include <arpa/inet.h>
#include <stdio.h>
/* ==> https://github.com/thom311/libnl/pull/73
#include <linux/if.h>
*/
#include <sys/ioctl.h>
#include <stdlib.h>
#include <unistd.h>

/* if_nametoindex() */
#include <net/if.h>
/* getifaddrs() */
#include <ifaddrs.h>
/* getnameinfo() */
#include <netdb.h>

/* Etienne Glossi - PACKET_MR_PROMISC */
#include <netpacket/packet.h>

/* list of addresses and interface numbers on local machine */
static struct {
	struct sockaddr_in dstaddr;
	int ifindex, raw_socket;
} ifs[MAXIFS];

/* Where we forge our packets */
static u_char gram[4096]=
{
	0x45,	0x00,	0x00,	0x26,
	0x12,	0x34,	0x00,	0x00,
	0xFF,	0x11,	0,	0,
	0,	0,	0,	0,
	0,	0,	0,	0,
	0,	0,	0,	0,
	0x00,	0x12,	0x00,	0x00,
	'1','2','3','4','5','6','7','8','9','0'
};

int main(int argc,char **argv)
{
	/* Debugging, forking, other settings */
	int debug, forking;

	u_int16_t port;
	u_char id;
	u_char ttl;

	/* We use two sockets - one for receiving broadcast packets (type UDP), and
	   one for spoofing them (type RAW) */
	int fd,rcv;

	/* Structure holds info on local interfaces */
	int maxifs;
	struct ifaddrs *ifaddr, *ifa;
	struct sockaddr_in *if_dest_addr;

	/* Address broadcast packet was sent from */
	struct sockaddr_in rcv_addr;

	/*  Etinene Glossi - packet_mr struct for receiving socket -> promiscious */
	struct {
		int	mr_ifindex;
		u_short	mr_type;
		u_short mr_alen;
		u_char	mr_address[8];
	} mr;

	/* Incoming message read via rcvsmsg */
	struct msghdr rcv_msg;
	struct iovec iov;
	u_char pkt_infos[16384];

	/* various variables */
	int x=1, len;

	struct cmsghdr *cmsg;
	int *ttlptr=NULL;
	int rcv_ifindex = 0;

	iov.iov_base = gram+ HEADER_LEN;
	iov.iov_len = 4006 - HEADER_LEN - 1;

	rcv_msg.msg_name = &rcv_addr;
	rcv_msg.msg_namelen = sizeof(rcv_addr);
	rcv_msg.msg_iov = &iov;
	rcv_msg.msg_iovlen = 1;
	rcv_msg.msg_control = pkt_infos;
	rcv_msg.msg_controllen = sizeof(pkt_infos);


	/* parsing the args */
	if(argc < 5)
	{
		fprintf(stderr,"usage: %s [-d] [-f] id udp-port dev1 dev2 ...\n",*argv);
		fprintf(stderr,"This program listens for broadcast packets on the specified udp-port\n"
			"and then forwards them to each other given interface.  Packets are sent\n"
			"such that they appear to have come from the original broadcaster. When using\n"
			"multiple instances for the same port on the same network, they must have the\n"
			"a different id.\n"
			"-d enables Debugging, -f forces forking to background\n");
		exit(1);
	};

	if ((debug = (strcmp(argv[1],"-d") == 0)))
	{
		argc--;
		argv++;
		DPRINT ("Debugging Mode enabled\n");
	};

	if ((forking = (strcmp(argv[1],"-f") == 0)))
	{
		argc--;
		argv++;
		DPRINT ("Forking Mode enabled (while debuggin? useless..)\n");
	};

	if ((id = atoi(argv[1])) == 0)
	{
		fprintf (stderr,"ID argument not valid\n");
		exit(1);
	}
	argc--;
	argv++;

	if (id < 1 || id > 99)
	{
		fprintf (stderr,"ID argument %i not between 1 and 99\n",id);
		exit(1);
	}
	ttl = id+TTL_ID_OFFSET;
	gram[8] = ttl;
	/* The is is used to detect packets we just sent, and is stored in the "ttl" field,
	 * which is not used with broadcast packets. Beware when using this with
	 * non-broadcast-packets */

	if ((port = atoi(argv[1])) == 0)
	{
		fprintf (stderr,"Port argument not valid\n");
		exit(1);
	}
	argc--;
	argv++;

	DPRINT ("ID: %i (ttl: %i), Port %i\n",id,ttl,port);

  /* List all the interfaces on the system */
	if (getifaddrs(&ifaddr) == -1) {
		perror("getifaddrs");
		exit(EXIT_FAILURE);
  }

	/* For each interface on the command line */
	for (maxifs=0;argc>1;argc--,argv++)
	{
		/*
		list interfaces on the system
		if current interface not in command line, continue
		*/

		/*
		then we check if we found all interfaces
		*/
		/* get interface index */
		int if_index = if_nametoindex(argv[1]);
		if (if_index <= 0) {
			fprintf (stderr,"Interface not found: %s\n",argv[1]);
			exit(1);
		}

		/* Save the index for later use */
		ifs[maxifs].ifindex = if_index;

		/* Get the IPv4 interface */
		for ( ifa = ifaddr;
					ifa != NULL &&
						!(ifa->ifa_addr->sa_family == AF_INET &&
						strncmp(ifa->ifa_name, argv[1], strlen(argv[1])) == 0);
					ifa = ifa->ifa_next);

		/* if the interface is not up or a loopback, ignore it */
		if ( ifa == NULL ||
				(ifa->ifa_flags & IFF_UP) == 0 ||
      	(ifa->ifa_flags & IFF_LOOPBACK) ) {
			printf("Ignoring interface %s\n", argv[1]);
			continue;
		}

		/* find the address type we need */
		if (ifa->ifa_flags & IFF_BROADCAST)
			if_dest_addr = (struct sockaddr_in*)(ifa->ifa_broadaddr);
		else
			if_dest_addr = (struct sockaddr_in*)(ifa->ifa_dstaddr);

		/* Save the address for later use */
		bcopy( if_dest_addr,
					 &ifs[maxifs].dstaddr,
					 sizeof(struct sockaddr_in) );

		DPRINT("%s: index=%i / broadcast=%s\n",
			ifa->ifa_name,
			ifs[maxifs].ifindex,
			inet_ntoa(ifs[maxifs].dstaddr.sin_addr));

		/* Set up a one raw socket per interface for sending our packets through */
		if((ifs[maxifs].raw_socket = socket(AF_INET,SOCK_RAW,IPPROTO_RAW)) < 0)
		{
			perror("socket");
			exit(1);
		};
		x=1;
		if (setsockopt(ifs[maxifs].raw_socket,SOL_SOCKET,SO_BROADCAST,(char*)&x,sizeof(x))<0)
		{
			perror("setsockopt SO_BROADCAST");
			exit(1);
		};
		/* bind socket to dedicated NIC (override routing table) */
		if (setsockopt(ifs[maxifs].raw_socket,SOL_SOCKET,SO_BINDTODEVICE,argv[1],strlen(argv[1])+1)<0)
		{
			perror("setsockopt IP_HDRINCL");
			exit(1);
		};
		/* Enable IP header stuff on the raw socket */
		#ifdef IP_HDRINCL
		x=1;
		if (setsockopt(ifs[maxifs].raw_socket,IPPROTO_IP,IP_HDRINCL,(char*)&x,sizeof(x))<0)
		{
			perror("setsockopt IP_HDRINCL");
			exit(1);
		};
		#else
		#error IP_HDRINCL support is required
		#endif

		/* ... and count it */
		maxifs++;
	}
	if(maxifs == 0) {
		fprintf(stderr, "No operationnal interfaces founds ! Please check ip network configuration.\n");
		exit(1);
	}
	/* well, we want the max index, actually */
	maxifs--;
	DPRINT("found %i interfaces total\n",maxifs+1);

  /* free our interfaces buffer */
	freeifaddrs(ifaddr);

	/* Create our broadcast receiving socket */
	if((rcv=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)) < 0)
  	{
  		perror("socket");
  		exit(1);
  	};

	x = 1;/*
	if(setsockopt(rcv, SOL_SOCKET, SO_BROADCAST, (char*) &x, sizeof(int))<0){
		perror("SO_BROADCAST on rcv");
		exit(1);
	};
	*/
	/* Etienne Glossi - promiscious mode */
	mr.mr_ifindex = 1;
	mr.mr_type = PACKET_MR_PROMISC;
	if(setsockopt(rcv, SOL_SOCKET, PACKET_ADD_MEMBERSHIP, (void*)&mr, sizeof(mr))<0){
		perror("PACKET_MR_PROMISC on rcv");
		exit(1);
	};

	if(setsockopt(rcv, SOL_IP, IP_RECVTTL, (char*) &x, sizeof(int))<0){
		perror("IP_RECVTTL on rcv");
		exit(1);
	};
	if(setsockopt(rcv, SOL_IP, IP_PKTINFO, (char*) &x, sizeof(int))<0){
		perror("IP_PKTINFO on rcv");
		exit(1);
	};

	/* We bind it to broadcast addr on the given port */
	rcv_addr.sin_family = AF_INET;
	rcv_addr.sin_port = htons(port);
	rcv_addr.sin_addr.s_addr = INADDR_ANY;

	if ( bind (rcv, (struct sockaddr *)&rcv_addr, sizeof(struct sockaddr_in) ) < 0 )
	{
		perror("bind");
		fprintf(stderr,"A program is already bound to the broadcast address for the given port\n");
		exit(1);
	}

	/* Set dest port to that was provided on command line */
	*(u_short*)(gram+22)=(u_short)htons(port);

 	/* Fork to background */
  if (! debug) {
    if (forking && fork())
      exit(0);

    fclose(stdin);
    fclose(stdout);
    fclose(stderr);
  }

  DPRINT("Done Initializing\n\n");

	for (;;) /* endless loop */
	{
		printf("packet");
		/* Receive a broadcast packet */
		len = recvmsg(rcv,&rcv_msg,0);
		if (len <= 0) continue;	/* ignore broken packets */

		/* Find the ttl and the receiving interface */
		ttlptr=NULL;
		if (rcv_msg.msg_controllen>0)
		  for (cmsg=CMSG_FIRSTHDR(&rcv_msg);cmsg;cmsg=CMSG_NXTHDR(&rcv_msg,cmsg)) {
		    if (cmsg->cmsg_type==IP_TTL) {
		      ttlptr = (int *)CMSG_DATA(cmsg);
		    }
		    if (cmsg->cmsg_type==IP_PKTINFO) {
		      rcv_ifindex=((struct in_pktinfo *)CMSG_DATA(cmsg))->ipi_ifindex;
		    }
		  }

		if (ttlptr == NULL) {
			perror("TTL not found on incoming packet\n");
			exit(1);
		}
		if (*ttlptr == ttl) {
			DPRINT ("Got local packge (TTL %i) on interface %i\n",*ttlptr,rcv_ifindex);
			continue;
		}


		gram[HEADER_LEN + len] =0;
		DPRINT("Got remote package:\n");
		// DPRINT("Content:\t%s\n",gram+HEADER_LEN);
		DPRINT("TTL:\t\t%i\n",*ttlptr);
		DPRINT("Interface:\t%i\n",rcv_ifindex);
		DPRINT("From:\t\t%s:%d\n",inet_ntoa(rcv_addr.sin_addr),rcv_addr.sin_port);

		/* copy sender's details into our datagram as the source addr */
		bcopy(&(rcv_addr.sin_addr.s_addr),(gram+12),4);
	  	*(u_short*)(gram+20)=(u_short)rcv_addr.sin_port;

		/* set the length of the packet */
		*(u_short*)(gram+24)=htons(8 + len);
		*(u_short*)(gram+2)=htons(28+len);

		/* Iterate through our interfaces and send packet to each one */
		for (x=0;x<=maxifs;x++)
		{
			if (ifs[x].ifindex == rcv_ifindex) continue; /* no bounces, please */

			/* Set destination addr ip - port is set already*/
			bcopy(&(ifs[x].dstaddr.sin_addr.s_addr),(gram+16),4);

			DPRINT ("Sent to %s:%d on interface %i\n",
				inet_ntoa(ifs[x].dstaddr.sin_addr), /* dst ip */
				ntohs(*(u_short*)(gram+22)), /* dst port */
				ifs[x].ifindex); /* interface number */

			/* Send the packet */
			if (sendto(ifs[x].raw_socket,
					&gram,
					28+len,0,
					(struct sockaddr*)&ifs[x].dstaddr,sizeof(struct sockaddr)
				) < 0)
				perror("sendto");
		}
		DPRINT ("\n");
	}
}
