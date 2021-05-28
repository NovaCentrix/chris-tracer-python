#!/usr/bin/env python3

import serial
from time import sleep
from datetime import datetime, timedelta

""" This script works with echo.py on the Pico (and main.py which imports echo and calls run()).  It works on iMac02 running
    python3.7, and the original Pico (late Jan 2021).
"""

with serial.Serial( '/dev/tty.usbmodem0000000000001',
                     baudrate = 115200,
                     stopbits = serial.STOPBITS_ONE,
                     bytesize = serial.EIGHTBITS,
                     writeTimeout = 0,
                     timeout = 10,
                     rtscts = False,
                     dsrdtr = False ) as ser:

    totalDiff = timedelta( seconds = 0.0 )

    for i in range( 100 ):
        startTime = datetime.now()
        ser.write( b'a' )
        answer = ser.readline()
        endTime = datetime.now()
        answer = answer.strip()
        if (len( answer ) != 100):
            print( "Incomplete answer, len =", len(answer) )
        totalDiff += endTime - startTime
        
    print( f"Average rt time: {totalDiff / 100.0}" )        
