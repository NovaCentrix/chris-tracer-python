# Proof of concept: Tiny 2040 + 0.49 in OLED + Shift Register

import sys
import select
from machine import I2C, SPI, Pin, Signal
import ssd1306
import ad8403
import utime
import tracer

def chprintable(ch):
  if ch == str(b'\x7f','ascii'): return False
  if ch < ' ': return False
  return True

# initialize the tracer module
tr = tracer.TraceR()

tr.display_splash_screen()
utime.sleep(3) # wait three seconds
tr.display_resistances_update()

# start serial console
echo = True
running = True
state_CMD = 0
state_DIGI = 1
state_OPER = 2
state_GET_VALUE = 3
state_SET_VALUE = 4
state_GET_RELAY = 5
state_SET_RELAY = 6
state_index = 0

show_values = False
state = state_CMD
last_state = state_CMD
cmd = 'R'
potnum = '1'
STR_PROMPT='\n> '
STR_ERROR='!'
print(STR_PROMPT, end='')
while running:
  while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:        
    ch = sys.stdin.read(1).upper()
    #if echo: print(state, ch,hex(ord(ch)))
    if chprintable(ch): 
      print(ch,end='')
    if ch == 'Q': running = False
    # command parser
    if state == state_CMD: # looking for command
      if ch == 'X': 
        cmd = 'X'
        state = state_DIGI
      elif ch == 'K': 
        cmd = 'K'
        state = state_DIGI
      else:
        print(STR_ERROR, end='')
        print(STR_PROMPT, end='')
    elif state == state_DIGI: # looking for digipot number
      state = state_CMD # assume failure...
      state_index = 0
      if ch == '1': 
        potnum = ch
        pot = tr.r1
        relay = tr.k1
        state = state_OPER
      elif ch == '2': 
        pot = tr.r2
        relay = tr.k2
        potnum = ch
        state = state_OPER
      else:
        state = state_CMD
        print(STR_ERROR, end='')

    elif state == state_OPER:
      if ch == '=': 
        if cmd == 'X': state = state_SET_VALUE
        if cmd == 'K': state = state_SET_RELAY
      elif ch == '?':
        if cmd == 'X': state = state_GET_VALUE
        if cmd == 'K': state = state_GET_RELAY
      elif ord(ch) == 0x0a:
        show_values = True
        state=state_CMD
      else:
        state = state_CMD
        print(STR_ERROR, end='')

    elif state == state_GET_VALUE:
      show_values = True
      state=state_CMD # start all over

    elif state == state_GET_RELAY:
      show_values = True
      state=state_CMD # start all over
      pass

    elif state == state_SET_VALUE:
      if state_index==0: val=''
      if ord(ch) == 0x0a:
        if state_index > 0:
          ival = int(val)
          pot.counts(ival)
          errs, checks = tr.chain.send()
          tr.display_counts_update()
          show_values = True
          state=state_CMD # start all over
        else:
          state = state_CMD
          print(STR_ERROR, end='')
      else:
        if ch.isdigit():
          val += ch
          state_index += 1
          ival = int(val)
          if ival < 0 or ival > 255:
            state = state_CMD
            print(STR_ERROR, end='')
        else:
          state = state_CMD
          print(STR_ERROR, end='')

    elif state == state_SET_RELAY:
      if state_index==0: val=''
      if ord(ch) == 0x0a:
        if state_index > 0:
          relay.set(ival)
          tr.display_counts_update()
          show_values = True
          state=state_CMD # start all over
      else:
        if ch.isdigit():
          val += ch
          state_index += 1
          ival = int(val)
          if ival < 0 or ival > 1:
            state = state_CMD
            print(STR_ERROR, end='')
        else:
          state = state_CMD
          print(STR_ERROR, end='')
      pass

    if show_values:
      count_status = 'X'+str(potnum)+'='+str(pot.vals[0])
      relay_status = 'K'+str(potnum)+'='+relay.get_string()
      print('\n', end='')
      print(count_status, relay_status, end='')
      show_values=False

    if last_state != state_CMD and state==state_CMD:
      print(STR_PROMPT,end='')

    last_state = state


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

