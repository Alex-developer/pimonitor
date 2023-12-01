from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, sh1107, ws0010

from PIL import ImageFont
from pathlib import Path
from enum import Enum
from packaging import version
from gpiozero import Button

from paramiko.ssh_exception import SSHException
from queue import Empty

from DFRobot_DF2301Q import *

import threading
import paramiko
import time
import queue
import picontrolslave
import signal

import hosts

class PICONTROL(threading.Thread) :
    OLEDWIDTH = 128
    STATES = Enum('STATE', 'Error Connecting Connected Installing Running Shutdown Pause Terminated')
    _state = STATES.Connecting
    _load = '??'
    _cpuTemp = '??'
    _allsky = '??'
    queue = None
    
    def __init__(self, group=None, target=None, name=None, queue=None, args=(), kwargs=None):
        super(PICONTROL,self).__init__(group=group, target=target, name=name)
        self._args = args
        self._host = kwargs['host']
        self.queue = queue
        
        self._serial = i2c(port=int(self._host['bus']), address=self._host['address'])
        self._device = ssd1306(self._serial)
        return
        
    def run(self) :

        while self._state is not self.STATES.Terminated:
                        
            self._updateDisplay()

            if self._state == self.STATES.Connecting:                
                self._connect()

            if self._state == self.STATES.Running:
                count = 1
                if self._getLoad():
                    if self._getTemp():
                        if self._getAllskyStatus():
                            self._updateDisplay()
                        
            if self._state == self.STATES.Shutdown:
                self._updateDisplay()
                stdout, stderr = self._runCommand(f"{self._host['home']}/picontrolslave.py -s")
                self._state = self.STATES.Pause
                
            if self._state == self.STATES.Pause:
                self._updateDisplay()
                time.sleep(20)
                self._state = self.STATES.Connecting
                
            if self._state is not self.STATES.Terminated:
                try:
                    val = self.queue.get(block=False)
                    if val == 'shutdown':
                        self.queue.task_done()
                        with self.queue.mutex:
                            self.queue.queue.clear()
                        self._state = self.STATES.Shutdown
                        time.sleep(0.5)
                    if val == 'terminate':
                        self._state = self.STATES.Terminated
                except Empty:
                    pass
                time.sleep(1)
 
        self._state = self.STATES.Terminated
        self._updateDisplay()
        
    def _connect(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._client.connect(hostname=self._host['ip'], username=self._host['user'], password=self._host['password'])
            self._state = self.STATES.Running
            
            sftp = self._client.open_sftp()
            try:
                sftp.stat('picontrolslave.py')
                stdout, stderr = self._runCommand(f"{self._host['home']}/picontrolslave.py -v")
                if not stderr:
                    clientVersion = version.parse(stdout)
                    localVersion = version.parse(picontrolslave.VERSION)
                    if localVersion > clientVersion:
                        print(f'Updated version {localVersion} available. Client has {clientVersion} - Updating')
                        self._installSlave(sftp)
                        self._state = self.STATES.Running
                else:
                    self._updateDisplay('Version Error')
            except FileNotFoundError:
                self._installSlave(sftp)
                self._state = self.STATES.Running
            except Exception as e:
                print(e)
                #print(type(e).__name__)
            sftp.close()
                
        except Exception as e:
            print(f"[!] Cannot connect to the SSH Server {self._host['ip']} using {self._host['user']}/{self._host['password']}")

    def _installSlave(self, sftp):
        self._state = self.STATES.Installing
        self._updateDisplay()

        sftp = self._client.open_sftp()
        try:
            result = sftp.put('install.sh', f"{self._host['home']}/install.sh")
            stdout, stderr = self._runCommand(f"chmod +x {self._host['home']}/install.sh")
            stdout, stderr = self._runCommand(f"{self._host['home']}/install.sh")            
            try:
                result = sftp.put('picontrolslave.py', f"{self._host['home']}/picontrolslave.py")
                stdout, stderr = self._runCommand(f"chmod +x {self._host['home']}/picontrolslave.py")
                print(result)
            except Exception as e:
                self._state = self.STATES.Error
                self._updateDisplay()
        except Exception as e:
            self._state = self.STATES.Error
            self._updateDisplay()

    def _runCommand(self, command):
        #print(f"command {command}")
        stdout = ''
        stderr = ''
        try:
            stdin, stdout, stderr = self._client.exec_command(command)
            stdout = stdout.read().decode().strip()
            stderr = stderr.read().decode().strip()
        except SSHException:
            self.STATES.Connecting
            stderr = 'Error'
        except Exception:
            pass
        
        #print(stdout)
        #print(stderr)
        return stdout, stderr
                                                         
    def _getLoad(self):
        result = False
        stdout, stderr = self._runCommand(f"{self._host['home']}/picontrolslave.py -c")
        if not stderr:
            self._load = stdout
            result = True
        else:
            self._state = self.STATES.Connecting
            
        return result

    def _getTemp(self):
        result = False        
        stdout, stderr = self._runCommand(f"{self._host['home']}/picontrolslave.py -t")
        if not stderr:
            self._cpuTemp = stdout
            result = True
        else:
            self._state = self.STATES.Connecting
            
        return result
         
    def _getAllskyStatus(self):
        result = False        
        stdout, stderr = self._runCommand(f"{self._host['home']}/picontrolslave.py -a")
        if not stderr:
            self._allsky = stdout
            result = True
        else:
            self._state = self.STATES.Connecting
            
        return result        
                           
    def _updateDisplay(self, error=''):
        headingFontSize = 14
        messageFontSize = 18
        messageSmallFontSize = 12
        margin_y_line = [0, 13, 26, 39, 52]

        headingFont = ImageFont.truetype(str(Path(__file__).resolve().parent.joinpath("fonts", "DejaVuSansMono.ttf")), headingFontSize)
        messageFont = ImageFont.truetype(str(Path(__file__).resolve().parent.joinpath("fonts", "DejaVuSansMono.ttf")), messageFontSize)
        messageSmallFont = ImageFont.truetype(str(Path(__file__).resolve().parent.joinpath("fonts", "DejaVuSansMono.ttf")), messageSmallFontSize)

        with canvas(self._device) as draw:
            x = self._getCenter(draw, self._host['name'], font=headingFont)
            draw.text((x, margin_y_line[0]), self._host['name'], font=headingFont, fill='white', align='center')
            
            if self._state == self.STATES.Error:
                x = self._getCenter(draw, error, font=messageFont)
                draw.text((x, margin_y_line[2]), error, font=messageFont, fill='white')
                            
            if self._state == self.STATES.Connecting:
                x = self._getCenter(draw, 'Connecting', font=messageFont)
                draw.text((x, margin_y_line[2]), 'Connecting', font=messageFont, fill='white')

            if self._state == self.STATES.Connected:
                x = self._getCenter(draw, 'Connected', font=messageFont)
                draw.text((x, margin_y_line[2]), 'Connected', font=messageFont, fill='white')
                
            if self._state == self.STATES.Installing:
                x = self._getCenter(draw, 'Installing', font=messageSmallFont)
                draw.text((x, margin_y_line[2]), 'Installing', font=messageSmallFont, fill='white')                
                x = self._getCenter(draw, 'Client Code', font=messageSmallFont)
                draw.text((x, margin_y_line[3]), 'Client Code', font=messageSmallFont, fill='white')  

            if self._state == self.STATES.Running:
                x = self._getCenter(draw, f"{self._host['ip']}", font=messageSmallFont)
                draw.text((x, margin_y_line[1]), f"{self._host['ip']}", font=messageSmallFont, fill='white')
                draw.text((0, margin_y_line[2]), f"Load: {self._load}", font=messageSmallFont, fill='white')                
                draw.text((0, margin_y_line[3]), f"Temp: {self._cpuTemp}°C", font=messageSmallFont, fill='white')                
                draw.text((0, margin_y_line[4]), f"Allsky: {self._allsky}", font=messageSmallFont, fill='white')                
                
            if self._state == self.STATES.Shutdown:
                x = self._getCenter(draw, 'Shutdown', font=messageFont)
                draw.text((x, margin_y_line[2]), 'Shutdown', font=messageFont, fill='white')
                        
            if self._state == self.STATES.Pause:
                x = self._getCenter(draw, 'Waiting For', font=messageSmallFont)
                draw.text((x, margin_y_line[2]), 'Waiting For', font=messageSmallFont, fill='white')                
                x = self._getCenter(draw, 'Shutdown', font=messageSmallFont)
                draw.text((x, margin_y_line[3]), 'Shutdown', font=messageSmallFont, fill='white')  
                     
            if self._state == self.STATES.Terminated:
                x = self._getCenter(draw, 'Terminated', font=messageFont)
                draw.text((x, margin_y_line[2]), 'Terminated', font=messageFont, fill='white')

                                                
        if self._state == self.STATES.Error:
            while True:
                time.sleep(1)
                    
    def _getCenter(self, draw, text, font):        
        left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font)
        width = right - left

        x = 0
        if width <= self.OLEDWIDTH:
            x = (self.OLEDWIDTH - width) // 2
        
        return x


class PIMANAGER():
    
    _running = True
    _panicButton = None
    _voice = None    
    _hosts = None

    def __init__(self, hosts):
        self._hosts = hosts
        self._panicButton = Button(14)    
        self._panicButton.when_pressed = self.panicPressed
        
        try:
            self._voice = DFRobot_DF2301Q_I2C(i2c_addr=DF2301Q_I2C_ADDR, bus=1)
            self._voice.set_volume(4)
            self._voice.set_mute_mode(0)
            self._voice.set_wake_time(20) 
        except:
            pass
        
        return
    
    def start(self):
        for host in self._hosts:
            q = queue.Queue()
            self._hosts[host]['thread'] = PICONTROL(queue=q, name=host, kwargs={'host': self._hosts[host]})

        for host in self._hosts:
            self._hosts[host]['thread'].start()

        while self._running:
            if self._voice is not None:
                voiceCommand = 0
                try:
                    voiceCommand = self._voice.get_CMDID()
                except:
                    pass
                if voiceCommand != 0:
                    print(f"CMDID = {voiceCommand}\n")
                    if voiceCommand == 5:
                        self.panicPressed()
                    if voiceCommand == 82:
                        self.terminate()
            time.sleep(0.5)

    def panicPressed(self):
        for host in self._hosts:
            self._hosts[host]['thread'].queue.put('shutdown')
            
    def terminate(self):
        for host in self._hosts:
            self._hosts[host]['thread'].queue.put('terminate')
            self._hosts[host]['thread'].join()
            
        self._running = False
    
if __name__ == "__main__":
    manager = PIMANAGER(hosts.PIHOSTS)
    manager.start()