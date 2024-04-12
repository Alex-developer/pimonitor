#!/home/pi/agvenv/bin/python3

import argparse
import os
import psutil
import json

VERSION = '1.0.23'
parser = argparse.ArgumentParser(description='Monitor controls', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-a', '--all', action='store_true', help='Get All data')

parser.add_argument('-u', '--up', action='store_true', help='Start Allsky')
parser.add_argument('-d', '--down', action='store_true', help='Stop Allsky')
parser.add_argument('-e', '--restart', action='store_true', help='Restart Allsky')

parser.add_argument('-s', '--shutdown', action='store_true', help='Shutdown')
parser.add_argument('-r', '--reboot', action='store_true', help='Reboot')
parser.add_argument('-v', '--version', action='store_true', help='Get Version Number')
args = parser.parse_args()
config = vars(args)

def bytesto(bytes, to, bsize=1024): 
    a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6 }
    r = float(bytes)
    return bytes / (bsize ** a[to])

if args.up:
    os.system('sudo systemctl start allsky')
    exit(0)

if args.down:
    os.system('sudo systemctl stop allsky')
    exit(0)

if args.restart:
    os.system('sudo systemctl restart allsky')
    exit(0)

        
if args.all:
    cpuLoad = psutil.cpu_percent(interval=1)

    temps = psutil.sensors_temperatures()
    cpuTemp = '??'
    for name, entries in temps.items():
        if name == 'cpu_thermal':
            cpuTemp = entries[0].current
            cpuTemp = float(cpuTemp)
            cpuTemp = round(cpuTemp,2)
            
    allskyRunning = 'allsky.sh' in (i.name() for i in psutil.process_iter())
    allskyRunningText = ''
    allskyStatus = 'Unknown'
    try:
        found = False
        allskyStatus = os.path.join(os.environ['ALLSKY_HOME'], 'config', 'status.json')
        if os.path.isfile(allskyStatus):
            found = True
    except Exception as e:
        pass
            
    if not found:            
        try:
            allskyStatus = os.path.join(os.environ['HOME'], 'allsky', 'config', 'status.json')
            if os.path.isfile(allskyStatus):
                found = True
        except Exception as e:
            pass
        
    if found:
        with open(allskyStatus) as file:
            data = json.load(file)
        allskyRunningText = data['status']


    if allskyRunningText == '':
        if allskyRunning:
            allskyRunningText = 'Running'
        else:
            allskyRunningText = 'Stopped'

    partitions = psutil.disk_partitions()
    total = 0
    used = 0
    free = 0
    for partition in partitions:
        partitionInfo = psutil.disk_usage(partition.mountpoint)
        total += partitionInfo.total
        used += partitionInfo.used
        free += partitionInfo.free
        
    total = int(bytesto(total, 'g'))
    free = int(bytesto(free, 'g'))
    used = int(bytesto(used, 'g'))
    usedPercent = (used/free) * 100
                                
    data = { 
        'cpu' : int(cpuLoad),
        'temp' : int(cpuTemp),
        'allsky': int(allskyRunning),
        'allskytext': allskyRunningText,
        'disk': used,
        'disksize': total
    }             

    print(json.dumps(data))
        
if args.version:
    print(VERSION)
    exit(0)

if args.reboot:
    os.system('sudo reboot')
    exit(0)
        
if args.shutdown:
    os.system('sudo poweroff')
    exit(0)