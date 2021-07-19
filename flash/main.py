# TraceR Module

gc.collect()
import sys, gc
gc.collect()
import tracer
gc.collect()
import select
gc.collect()
import utime
gc.collect()

def chprintable(ch):
  if ch == str(b'\x7f','ascii'): return False
  if ch < ' ': return False
  return True

def show_help():
  try:
    with open( 'help.txt', 'r') as fhelp:
      for line in fhelp:
        print(line, end='')
  except OSError:
    pass

class Display_control:
  def __init__(self, counts=False, relays=False, ohms=False, identity=False):
    self.counts = counts
    self.relays = relays
    self.ohms = ohms
    self.identity = identity

def doit():
  print('TraceR Module Initializing...')

  display = Display_control()

  calibrated = False
  serno = 'unk'
  # First thing is to check that there is a calibration,
  # and that both calibration files are consistent:
  #   (1) both have the same serial number, and
  #   (2) cal1 is R1, cal2 is R2
  # If data is consistent, set the unit into the
  # calibrated state
  # Note: cal1 and cal2 are loaded by boot.py
  if cal1.serno == cal2.serno:
    if cal1.resno == 'R1' and cal2.resno == 'R2':
      serno = cal1.serno
      calibrated = True

  if calibrated:
    print('Calibrated unit,', serno)
  else:
    print('Uncalibrated unit')
  print('Type "H" for help')



  # initialize the tracer module
  tr = tracer.TraceR()

  tr.display_splash_screen(serno)
  utime.sleep(3) # wait three seconds

  # initialize TraceR
  tr.k1.open()
  tr.k2.open()
  if calibrated:
    regs = cal1.lookup(100)
    tr.r1.counts(regs.regs)
    tr.r1.cal = regs
    regs = cal2.lookup(50)
    tr.r2.counts(regs.regs)
    tr.r2.cal = regs
    errs, checks = tr.chain.send()
    tr.display_ohms_update()
  else:
    tr.r1.counts(64)
    tr.r2.counts(128)
    errs, checks = tr.chain.send()
    tr.display_counts_update()


  # start serial console
  echo = True
  running = True
  state_UNK = -1
  state_CMD = 0
  state_DIGI = 1
  state_OPER = 2
  state_GET_COUNTS = 3
  state_SET_COUNTS = 4
  state_GET_RELAY = 5
  state_SET_RELAY = 6
  state_GET_OHMS = 7
  state_SET_OHMS = 8
  state_IDENTITY = 9
  state_QUIT = 99
  state_index = 0

  show_values = False
  state = state_CMD
  last_state = state_CMD
  cmd = 'R'
  STR_PROMPT='\n> '
  STR_ERROR='!'
  print(STR_PROMPT, end='')
  sides=[]
  while running:
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:        
      ch = sys.stdin.read(1).upper()
      #if echo: print(state, ch,hex(ord(ch)))
      if chprintable(ch): print(ch,end='')
      if ch == 'Q': 
        running = False
        state = state_QUIT
      # command parser
      if state == state_CMD: # looking for command
        if ch == 'X': 
          cmd = 'X'
          state = state_DIGI
        elif ch == 'K': 
          cmd = 'K'
          state = state_DIGI
        elif ch == 'R' and calibrated:
          cmd = 'R'
          state = state_DIGI
        elif ch == 'H': 
          show_help()
          last_state = state_UNK
        elif ch == 'I': 
          cmd = 'I'
          state = state_IDENTITY
        elif ord(ch) == 0x0a: # show status
          show_values = True
          sides = [(tr.r1, tr.k1, cal1),
                   (tr.r2, tr.k2, cal2)]
          display.counts = True
          display.relays = True
          display.ohms = True
          last_state = state_UNK
        else:
          print(STR_ERROR, end='')
          print(STR_PROMPT, end='')

      elif state == state_IDENTITY:
        if ord(ch) == 0x0a:
          show_values = True
          display.identity = True
          state=state_CMD # start all over
        else:
          print(STR_ERROR, end='')
          state=state_CMD

      elif state == state_DIGI: # looking for digipot number
        state = state_CMD # assume failure...
        state_index = 0
        if ch == '1': 
          sides = [(tr.r1, tr.k1, cal1)]
          state = state_OPER
        elif ch == '2': 
          sides = [(tr.r2, tr.k2, cal2)]
          state = state_OPER
        else:
          state = state_CMD
          print(STR_ERROR, end='')

      elif state == state_OPER:
        if ch == '=': 
          if cmd == 'X': state = state_SET_COUNTS
          if cmd == 'K': state = state_SET_RELAY
          if cmd == 'R': state = state_SET_OHMS
        elif ch == '?':
          if cmd == 'X': state = state_GET_COUNTS
          if cmd == 'K': state = state_GET_RELAY
          if cmd == 'R': state = state_GET_OHMS
        elif ord(ch) == 0x0a:
          if cmd == 'X':
            show_values = True
            display.counts = True
            state=state_CMD # start all over
          if cmd == 'K':
            show_values = True
            display.relays = True
            state=state_CMD # start all over
          if cmd == 'R':
            show_values = True
            display.ohms = True
            state=state_CMD # start all over
        else:
          state = state_CMD
          print(STR_ERROR, end='')

      elif state == state_GET_COUNTS:
        show_values = True
        display.counts = True
        state=state_CMD # start all over

      elif state == state_GET_RELAY:
        show_values = True
        display.relays = True
        state=state_CMD # start all over

      elif state == state_GET_OHMS:
        show_values = True
        display.ohms = True
        state=state_CMD # start all over

      elif state == state_SET_COUNTS:
        if state_index==0: val=''
        if ord(ch) == 0x0a:
          if state_index > 0:
            ival = int(val)
            for pot,relay,cal in sides: 
              pot.counts(ival)
            errs, checks = tr.chain.send()
            show_values = True
            display.counts = True
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

      elif state == state_SET_OHMS:
        if state_index==0: val=''
        if ord(ch) == 0x0a:
          if state_index > 0:
            ival = int(val)
            for pot, relay, cal in sides: 
              regs = cal.lookup(ival)
              pot.counts(regs.regs)
              pot.cal = regs
            errs, checks = tr.chain.send()
            show_values = True
            display.ohms = True
            state=state_CMD # start all over
          else:
            state = state_CMD
            print(STR_ERROR, end='')
        else:
          if ch.isdigit():
            val += ch
            state_index += 1
            ival = int(val)
            if ival < 0 or ival > 300:
              state = state_CMD
              print(STR_ERROR, end='')
          else:
            state = state_CMD
            print(STR_ERROR, end='')
      elif state == state_SET_RELAY:
        if state_index==0: val=''
        if ord(ch) == 0x0a:
          if state_index > 0:
            for pot, relay, cal in sides: 
              relay.set(ival)
            show_values = True
            display.relays = True
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
      elif state == state_QUIT:
        print('\nGoodbye.')
        break

      if show_values:
        if display.identity:
          print('\n', end='')
          print('ID='+serno, end='')

        for pot, relay, cal in sides:
          if display.counts:
            print('\n', end='')
            count_status = 'X'+pot.chipid+'='+str(pot.vals[0])
            print(count_status, end='')
            tr.display_counts_update()
          if display.relays:
            print('\n', end='')
            relay_status = 'K'+relay.relayid+'='+relay.get_string()
            print(relay_status, end='')
            tr.display_counts_update()
          if display.ohms:
            print('\n', end='')
            if pot.cal is None:
              ohms_status = 'R'+pot.chipid+'='+'uncalibrated'
            else:
              ohms_status = 'R'+pot.chipid+'='+str(pot.cal.ract)
            print(ohms_status, end='')
            tr.display_ohms_update()
        display.counts = False
        display.relays = False
        display.ohms = False
        display.identity = False
        sides=[]
        show_values=False

      if last_state != state_CMD and state==state_CMD:
        print(STR_PROMPT,end='')

      last_state = state

doit()

