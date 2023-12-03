import time
import RPi.GPIO as GPIO

rebootPin = 27
greenLEDPin = 20
redLEDPin = 21

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(rebootPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(greenLEDPin, GPIO.OUT, initial=1)
GPIO.setup(redLEDPin, GPIO.OUT, initial=0)

def shut_down():
    GPIO.output(redLEDPin, 1)
    GPIO.output(greenLEDPin, 0)  
    command = '/usr/bin/sudo reboot'
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)


while True:
    GPIO.wait_for_edge(rebootPin, GPIO.FALLING)
    shut_down() 