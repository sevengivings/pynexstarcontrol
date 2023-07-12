# This script is based on the following script: https://github.com/akkana/scripts/blob/master/rpi/pyirw.py
# It opens a socket connection to the lirc daemon and parses the commands that the daemon receives
# It then checks whether a specific command was received and generates output accordingly

import os
import socket
from gpiozero import Motor
import time 
import queue 
import threading
import serial 
from tendo import singleton

me = singleton.SingleInstance() 

SOCKPATH = "/var/run/lirc/lircd"
sock = None

motor = Motor(forward=21, backward=20)

port = "/dev/ttyUSB0"
baud = 9600

queueKey = queue.Queue() 

# Establish a socket connection to the lirc daemon
def init_irw():
    global sock
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCKPATH)

    print ("Press 'E' of IrDA remocon or Ctrl-C to exit program.")
    print ("Press 'C' for shutdown of RPi, Press 'D' to reboot RPi.")
    print ("To adjust rotation rate, use '0'(down to 2) and 'F'(up to 7) key.")

# parse the output from the daemon socket
def getKey():    
    while True:
        data = sock.recv(128)
        data = data.strip()

        if (len(data) > 0):
            words = data.split()
            queueKey.put(words)

def readthread(ser): 
    while True: 
        if (ser.inWaiting() > 0):
            data_str = ser.read(ser.inWaiting()).decode('ascii') 
            # print(data_str, end='')
        
def sendslewcommand(ser, azm, positive, rate): 
    if azm: 
        if positive: 
            data = chr(80) + chr(2) + chr(16) + chr(36) + chr(rate) + chr(0) + chr(0) + chr(0)
        else:
            data = chr(80) + chr(2) + chr(16) + chr(37) + chr(rate) + chr(0) + chr(0) + chr(0)
    else: 
        if positive: 
            data = chr(80) + chr(2) + chr(17) + chr(36) + chr(rate) + chr(0) + chr(0) + chr(0)
        else:
            data = chr(80) + chr(2) + chr(17) + chr(37) + chr(rate) + chr(0) + chr(0) + chr(0)
    
    data = bytes(data,'ascii')
    ser.write(data)
    time.sleep(0.1)     

def controlNexstar(event):  
    rate = 7
    last_azm = True 
    
    while True:
        words = queueKey.get()
        key = words[2].decode()     
        repeat = words[1].decode()       

        if (key == "KEY_E"):
            break
        elif (key == "KEY_D"):
            os.system('sudo reboot')
        elif (key == "KEY_C"): 
            os.system('sudo shutdown -h now')
        elif (key == "KEY_LEFT"):
            motor.forward() 
            event.wait(0.05)
            motor.stop()
        elif (key == "KEY_RIGHT"):
            motor.backward() 
            event.wait(0.05)
            motor.stop()
        elif (key == "KEY_UP"):
            motor.forward() 
        elif (key == "KEY_DOWN"):
            motor.backward() 
        elif (key == "KEY_OK"): 
            motor.stop()
        elif (key == "KEY_NUMERIC_4"): 
            sendslewcommand(ser, True, False, rate)
            last_azm = True 
        elif (key == "KEY_NUMERIC_6"): 
            sendslewcommand(ser, True, True, rate)
            last_azm = True 
        elif (key == "KEY_NUMERIC_2"): 
            sendslewcommand(ser, False, True, rate)
            last_azm = False 
        elif (key == "KEY_NUMERIC_8"): 
            sendslewcommand(ser, False, False, rate)
            last_azm = False 
        elif (key == "KEY_NUMERIC_5"):   
            if last_azm: 
                sendslewcommand(ser, True, True, 0)
            else:
                sendslewcommand(ser, False, True, 0) 
            rate = 7
        elif (key == "KEY_NUMERIC_0"): 
            rate = rate - 1
            if (rate < 2): 
                rate = 2
        elif (key == "KEY_F"): 
            rate = rate + 1 
            if (rate > 7): 
                rate = 7

# Main entry point
# The try/except structures allows the users to exit out of the program
# with Ctrl + C. Doing so will close the socket gracefully.
if __name__ == '__main__':  
    try:
        ser = serial.Serial(port, baud, timeout=1)
        event = threading.Event()       

        init_irw()

        t1 = threading.Thread(target=getKey, daemon=True) 
        t1.start() 

        t2 = threading.Thread(target=controlNexstar, args=(event,))
        t2.start()
        
        t3 = threading.Thread(target=readthread, args=(ser,), daemon=True)
        t3.start()         
        
        t2.join()
    except KeyboardInterrupt:
        print ("\nShutting down...")
        # Close the socket (if it exists)
        if (sock != None):
            sock.close()
        if (ser != None): 
            ser.close() 
    except serial.serialutil.SerialException: 
        print ("No Nexstar connection found. Electonic focusser will work only.\n")

        event = threading.Event()

        init_irw()

        t1 = threading.Thread(target=getKey, daemon=True)
        t1.start()

        t2 = threading.Thread(target=controlNexstar, args=(event,))
        t2.start()        

        t2.join()
    finally:
        print ("pynexstarcontrol.py is done!\n")
