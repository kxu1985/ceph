#!/usr/bin/env python
import sys
import optparse
import random
import time
import urllib
import subprocess
import json

#==========================
# Define osd containers
#==========================
osd_container = {}

#==========================
#  Input Your Object Name
#==========================
objname = raw_input('Create an object name: ')
filename = raw_input('Give the file name you want to store: ')

#==========================
#  Find PG# and OSD#
#==========================
proc = subprocess.Popen(['ceph', 'osd', 'map', 'ke-demo', objname], stdout=subprocess.PIPE)
lineOut = proc.stdout.readlines()[0].rstrip()
print lineOut
arrLineOut = lineOut.split()
#print arrLineOut
pg = arrLineOut[10]
idx = 0
for s in arrLineOut[13]:
	if s == '[':
		startInd = idx + 1
	if s == ']':
		endInd = idx
	idx = idx + 1
osd = arrLineOut[13][startInd:endInd].split(',')
for i in osd:
	osd_container[i] = {'id': i, 'pg': pg}

print "\nStorage info:"
print 'PG (placement group): ' + pg
print 'OSD devices: ', osd

#============================
#  Find IP addresses of OSDs
#============================
subprocess.call("ceph osd dump -o tmp.json --format=json", shell=True)
osdDump = json.loads(open("tmp.json").read())
subprocess.call("rm -rf tmp.json", shell=True)
ip = []
for i in osd:
	tmp_ip = str(osdDump['osds'][int(i)]['public_addr']).split(':')[0]
	osd_container[i]['ip'] = tmp_ip
	ip.append(tmp_ip)

#print json.dumps(osdDump, indent=2)
print 'OSD IP: ', ip, '\n'
print 'OSD Container: ', osd_container, '\n'

#===================================
# Find Hosts mapped to IP addresses
#===================================
f_host = open('/etc/hosts','r')
host = []
while True:
	line = f_host.readline().split()
	#print line
	if not line:
		break;
	for i in ip:
		if line[0] == i:
			host.append(line[1])
			for oid, items in osd_container.iteritems():
				if items['ip'] == i:
					osd_container[oid]['host'] = line[1]
					break
		
print 'Hosts: ', host, '\n'
print 'OSD Container: ', osd_container, '\n'
	
#======================================
# ssh into hosts and get latency stats
#======================================
for oid, items in osd_container.iteritems():
	subprocess.call("ssh -t "+items['host']+" 'sudo ceph --admin-daemon \/var\/run\/ceph\/ceph-osd*asok perf dump > \/home\/ceph\/tmp.json' &> /dev/null", shell=True)
	subprocess.call("scp "+items['host']+":/home/ceph/tmp.json ./ &> /dev/null", shell=True)
	perfDump = json.loads(open("./tmp.json").read())
	osd_container[oid]['avgPrimaryLatency'] = float(perfDump['recoverystate_perf']['primary_latency']['sum'])/int(perfDump['recoverystate_perf']['primary_latency']['avgcount'])
	osd_container[oid]['avgPeeringLatency'] = float(perfDump['recoverystate_perf']['peering_latency']['sum'])/int(perfDump['recoverystate_perf']['peering_latency']['avgcount'])
	#avgLatency = perfDump['osd']['op_w_latency']['sum']/perfDump['osd']['op_w_in_bytes'] * 1024 * 1024
	
	print 'Average Primary Lantency', osd_container[oid]['avgPrimaryLatency'], 'ms'
	print 'Average Peering Lantency', osd_container[oid]['avgPeeringLatency'], 'ms'
	#print 'Average Write Latency', avgLatency, 'ms/Mb\n'

	print 'Contacting OpenDayLight controller...'
	print 'Prioritizing flows for ceph OSDs...'
	print 'Executing QoS optimizing:'
	print 'ovs-vsctl set port <port-number-to-osd-host> qos=@newqos create qos type=linux-htb queues=0=q0 -- -id=@q0 create queue other-config:min-rate=<rate eg.2000000 for 2Mbps> other-config:max-rate=<rate>\n'

print 'Write content to Ceph OSD.'
print 'rados put <object name> <files> --pool=<pool name>'

