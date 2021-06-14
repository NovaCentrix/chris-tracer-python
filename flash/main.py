# Proof of concept: Tiny 2040 + 0.49 in OLED + Shift Register

import sys
import select
from machine import I2C, SPI, Pin, Signal
import ssd1306
import ad8403
import utime
import tracer


def display_resistances_update(disp, pots):
  """Update resistance values on screen."""
  disp.fill(0)
  disp.text("R1=", 2,2)
  disp.text(str(int(pots[0].Rcombine()[0]+0.5)), 32,2)
  disp.text("R2=", 2,15)
  disp.text(str(int(pots[1].Rcombine()[0]+0.5)), 32,15)
  disp.show()

def display_splash_screen(disp):
  """Welcome screen."""
  disp.text("Welcome to", 2,1)
  disp.text("to the", 2,11)
  disp.text("TraceR", 2,21)
  disp.show()

i2c = I2C(0, scl=Pin(1), sda=Pin(0))
disp = ssd1306.SSD1306_I2C(64, 32, i2c)


# initialize the Digipot chain
r1 = ad8403.Digipot()
r2 = ad8403.Digipot()
pots = [ r1, r2 ]
chain = ad8403.Digichain(digipots=pots)

display_splash_screen(disp)
utime.sleep(3) # wait three seconds
display_resistances_update(disp, pots)

# start serial console
echo = True
running = True
state_CMD = 0
state_DIGI = 1
state_VAL = 2
state_GO = 3
state_index = 0

state = state_CMD

while running:
  while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:        
    ch = sys.stdin.read(1)
    if echo: print(state, ch,hex(ord(ch)))
    #if echo: print(ch,end='')
    if ch == 'Q': running = False
    # command parser
    if state == state_CMD: # looking for command
      if ch == 'R': 
        cmd = 'R'
        state = state_DIGI
    elif state == state_DIGI: # looking for digipot number
      state = state_CMD # assume failure...
      state_index = 0
      if ch == '1': 
        rpot = r1
        state = state_VAL
      elif ch == '2': 
        rpot = r2
        state = state_VAL
    elif state == state_VAL:
      if state_index==0: val=''
      val += ch
      state_index += 1
      if ord(ch) == 0x0a:
        # take action
        print( cmd, int(val))
        rpot.counts(int(val))
        errs, checks = chain.send()
        display_resistances_update(disp, pots)
        state=state_CMD # start all over


####    r1.counts(0xc0)
####    r2.counts(0x40)
####    errs, checks = chain.send()
####    
####    disp.fill(0)
####    disp.text("R1=", 2,2)
####    disp.text(str(100), 32,2)
####    disp.text("R2=", 2,15)
####    disp.text(str(220), 32,15)
####    disp.show()

