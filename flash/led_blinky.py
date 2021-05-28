# Tiny 2040 RBG LED control
# Tony Goodhew 11th March 2021

import utime
from machine import Pin, PWM

#Setup RGB LED
# Construct PWM objects with RGB LED
rpwm = PWM(Pin(18)) # RED
gpwm = PWM(Pin(19)) # GREEN
bpwm = PWM(Pin(20)) # BLUE
# Set the PWM frequency.
rpwm.freq(1000)
gpwm.freq(1000)
bpwm.freq(1000)
# Turn off
rduty = 65535
gduty = 65535
bduty = 65535
rpwm.duty_u16(rduty)
gpwm.duty_u16(gduty)
bpwm.duty_u16(bduty)

def LED(r,g,b):
    rduty = int(65535 -(65535 * r/255))
    gduty = int(65535 -(65535 * g/255))
    bduty = int(65535 -(65535 * b/255))
#    print(rduty)
#    print(gduty)
#    print(bduty)
    rpwm.duty_u16(rduty)
    gpwm.duty_u16(gduty)
    bpwm.duty_u16(bduty)
    
LED(255,255,255)
utime.sleep(0.3)
LED(255,0,0)
utime.sleep(0.3)
# Blink
for i in range(4):
    LED(0,0,255)
    utime.sleep(0.3)
    LED(0,0,0)
    utime.sleep(0.3)
# Fade UP
for i in range(255):
    LED(i,i,0)
    utime.sleep(0.01)
# Fade DOWN
for ii in range(255,-1,-1):
    LED(ii,ii,0)
    utime.sleep(0.01)