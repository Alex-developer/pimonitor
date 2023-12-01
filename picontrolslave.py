#!/home/pi/agvenv/bin/python3

import argparse
import os
import psutil

VERSION = '1.0.23'
parser = argparse.ArgumentParser(description="Just an example", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-a", "--allsky", action="store_true", help="Get Allsky Status")
parser.add_argument("-i", "--ip", action="store_true", help="Get IP Address")
parser.add_argument("-c", "--cpu", action="store_true", help="Get CPU Load")
parser.add_argument("-t", "--temp", action="store_true", help="Get CPU Temp")
parser.add_argument("-s", "--shutdown", action="store_true", help="Shutdown")
parser.add_argument("-v", "--version", action="store_true", help="Get Version Number")
args = parser.parse_args()
config = vars(args)
#print(config)

if args.allsky:
    running = 'allsky.sh' in (i.name() for i in psutil.process_iter())
    if running:
        print('Online')
    else:
        print('Offline')
    exit(0)
    
if args.version:
    print(VERSION)
    exit(0)
    
if args.cpu:
    load = psutil.cpu_percent(interval=1)
    print(load)
    exit(0)

if args.temp:    
    temps = psutil.sensors_temperatures()
    cpuTemp = '??'
    for name, entries in temps.items():
        if name == 'cpu_thermal':
            cpuTemp = entries[0].current
            cpuTemp = float(cpuTemp)
            cpuTemp = round(cpuTemp,2)
    print(cpuTemp)            
    exit(0)
    
if args.shutdown:
    print('shutting down')
    os.system('sudo poweroff')
    exit(0)