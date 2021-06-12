''' Analog Devices AD840x Digipot Class

This class is to write to a pair of Digipots which are
connected in a daisy chain as described in the datasheet.


# Basic description, SPI registers:

Each Digipot has one 10-bit register, composed as follows:
  * 2-bits Address, [ A1, A0 ]  b9 -- b8
  * 8-bits Data,  [ D7 -- D0 ]  b7 -- b0

Digipots in this family may have up to four in a single chip
  * Value of 0x00:  R.WB = 0 ohms,  R.WA = Maximum
  * Value of 0xFF:  R.WB = Maximum, R.WB = 0 ohms

Control pins (hardcoded for now):
  /SHDN  GP27
  /RS    GP36
  /SS    GP5


# Note about SPI communications with Digipot

Due to some limitations of the SPI implementation in Micropython for the
RP2 (and others?), it's not straightforward to send an arbitrary number
of bits, such as 10 or 20. Instead of wrestling with the SPI driver
to make it work correctly for 10 or 20 bits, we will send an integer 
number of bytes and just throw away any remainders. In the case of
talking to one Digipot two bytes are send -- three digipots, 3 bytes

  * 6 dummy bits +   10 bits  ==  2 bytes (one digipot)
  * 4 dummy bits + 2*10 bits  ==  3 bytes (two digipots)

The code down below in function self.send() which is 
used to transmit wiper data over SPI requires some explanation.

* This family of Digipot has no provision to read back the wiper
  settings. The best we can do is to confirm the command we send
  is properly shifted through both shift registers and received
  back at the microcontroller on the MISO pin.

* Normally you would keep the /CS line high, only making it
  active (low) when communicating with the chip(s). But in this
  circuit, we have no other devices on the SPI, so we can let
  the /CS signal idle in the active (low) state. Why?

* Not only does the chip not have a read back ability, there is
  no "pass through" possible to shift out the previous command.

  - If /CS is high, the digital part of the chip is unresponsive.

  - The /CS transition from low to high is that loads the shift
    register values into the wiper control registers.

* The solution, keep /CS low all the time. When you want to
  write a value to the wipers, do the following:

  - keep /CS low...
  - shift in 20 (24) bits of new command values
  - toggle /CS high then low, thus loading the wipers
  - shift in 20 (24) bits of dummy data, and
  - capture the loopbacked MISO data 
  - the loopback data should match the commmanded data
    (after compensating for the extra four bits shift due 
    to the 20/24 bits issue)

That's the best you can do without external analog resistance 
monitoring hardware, or using a different kind of digital
potentiometer. The approach used in this code keeps track of 
current wiper values as follows:

1. On power up, issue a reset to the chip. This puts it in a
   known, mid-scale point according to the datasheet: 0x80 counts.

2. We keep track of the status of the Digipots be shadowing the
   command each time a new command is sent. This is kept in the class
   instance variable, of type list, called `values`.

'''

from machine import I2C, SPI, Pin, Signal
import utime
import binascii

# Each Digipot has one 10-bit register, composed as follows:
#   * 2-bits Address, [ A1, A0 ]  b9 -- b8
#   * 8-bits Data,  [ D7 -- D0 ]  b7 -- b0

# class Wiper:
#   def __init__(self):
#     self.chan = 0
#     self.cnts = 0x80
#     self.cmd = 0x080
# 
#   def command(self, _counts = None, _channel = None ):
#     if _channel is not None and _counts is not None:
#       self.cmd = (_channel & 0x3) << 8
#       self.cmd += _counts & 0xff
#     else:
#       self.cmd = (self.chan & 0x3) << 8
#       self.cmd += self.cnts & 0xff
# 
#   def counts(self, _counts, _channel = None):
#     pass



class Digipot:

  R1 = 0
  R2 = 1
  CH1 = 0
  CH2 = 1
  CH3 = 2
  CH4 = 3
  CH_ALL = None
  R_TOTAL = 1000  # total ohms
  R_WIPER = 0  # wiper resistance, ohms

  def __init__(self, _spi=0, _baudrate=100_000,
              _pin_ss = 5, _pin_shdn = 27, _pin_rst = 26,
              _firstbit = SPI.MSB, _polarity = 0, _phase = 1,
              _pin_sck = 6, _pin_mosi = 7, _pin_miso = 4,
              ):

    self.npots = 2
    self.nchans = 4

    self.spi = SPI(_spi, baudrate=_baudrate, 
                  # firstbit = _firstbit,
                  # polarity=_polarity, phase=_phase, 
                  # sck=Pin(_pin_sck), 
                  # mosi=Pin(_pin_mosi),
                  # miso=Pin(_pin_miso)
               )
    # Define pullup on MISO pin:
    # --------------------------
    # This was tough to figure out out
    # * This is done internally in the Micropython I2C init code, 
    #   but not in the SPI init code for some reason.
    # * The C version of doing this can be found in the 
    #   "Raspberry Pi Pico C/C++ SDK" p.280 in the 
    #    example program lcd_1602_i2c.c
    # * It seems that individual pins that are otherwise
    #   dedicated to a peripheral like the SPI bus can have 
    #   their pull-up and pull-down resistors controlled
    #   independently of that GPIO pin's peripherap assignment.
    #
    # Looking at the Micropython code for RP2 machine.Pin,
    # you can adjust the pullups / pulldowns as follows:
    Pin( _pin_miso, None, pull = Pin.PULL_UP )

    #print('SPI engine initialized')
    #print('Pin  sck:', Pin(_pin_sck))
    #print('Pin mosi:', Pin(_pin_mosi))
    #print('Pin miso:', Pin(_pin_miso))
    
    self.ss_pin = Pin(_pin_ss, Pin.OUT, value=1)
    self.ss = Signal(self.ss_pin, invert=True)
    self.shdn_pin = Pin(_pin_shdn, Pin.OUT, value=1) 
    self.shdn = Signal(self.shdn_pin, invert=True)
    self.rst_pin = Pin(_pin_rst, Pin.OUT, value=1) 
    self.rst = Signal(self.rst_pin, invert=True)
    
    # vals stores the digipot wiper counts, 0 to 255
    # cmds stores the corresponding 10-bit commands
    self.vals = [[0x80,0x80,0x80,0x80], 
                 [0x80,0x80,0x80,0x80]]
    self.cmds = [[0x080, 0x180, 0x280, 0x380], 
                 [0x080, 0x180, 0x280, 0x380]]
    self.verbose = True

    self.operate()
    self.select()
    self.reset()
    
  def cmd_parse(self, multi):
    cmd0 = (multi & (0x2ff << 10)) >> 10
    cmd1 = multi & 0x2ff
    cmd0_addr = (cmd0 & 0x200) >> 8
    cmd1_addr = (cmd1 & 0x200) >> 8
    cmd0_value = cmd0 & 0xff
    cmd1_value = cmd1 & 0xff
    return 'u2.w'+str(cmd0_addr)+'.v'+str(cmd0_value)+' vs '+\
           'u1.w'+str(cmd1_addr)+'.v'+str(cmd1_value)

  def status(self):
    print( 'select:', self.ss.value(), 
           'shutdown:', self.shdn.value(), 
           'reset:', self.rst.value(),
           'counts:', self.vals )

  def get_channel_list(self, channels):
    clist = []
    if channels is None:
        clist = [ c for c in range(self.nchans) ]
    elif type(channels) is int:
        clist = [ channels ]
    # bail out if channels isn't a list
    elif channels is not list:
        print('channels is not a list')
    return clist

  def ohms(self, digipot=0, channels=None ):
    # calculating Rwb, which is how the tracer is wired
    g = 0
    rtotal=0.0
    reach=[]
    for c in self.get_channel_list(channels):
      r  = float( self.vals[digipot][c] ) / 256.0
      r *= Digipot.R_TOTAL 
      r += Digipot.R_WIPER
      reach.extend( [r] )
    zero = False
    for r in reach:
      if r == 0: 
        zero = True
        break
      else: 
        g += 1.0 / r
    if zero:
      rtotal = 0.0
    else:
      rtotal = 1.0 / g
    print( rtotal, reach )

  # this function calculates the SPI command
  # for each of the four Digipots, or all
  # it will accept a single channel, a list of channels,
  # or None which sets all Digipots at once
  def counts(self, value, digipot=0, channels=None ):
    if channels is None:
        channels = [ c for c in range(4) ]
    elif type(channels) is int:
        channels = [ channels ]
    # bail out if channels isn't a list
    elif channels is not list:
        print('channels is not a list')
        return
    for c in channels:
        chan = c & 0x3
        command = chan << 8
        command += (value & 0xff)
        self.vals[digipot][chan] = value
        self.cmds[digipot][chan] = command
    if self.verbose:
        self.status()
        
  def send( self, channels=None ):
    if channels is None:
        channels = [ c for c in range(4) ]
    elif type(channels) is int:
        channels = [ channels ]
    # bail out if channels isn't a list
    elif channels is not list:
        print('channels is not a list')
        return

    errs = []
    checks = []
    for c in channels:      
        command =  (self.cmds[0][c] & 0x3ff) << 10
        command += (self.cmds[1][c] & 0x3ff)
        xbuff = bytearray( command.to_bytes(3, 'big'))
        rbuff = bytearray(b'\x12\x34\x56')
        self.spi.write_readinto( xbuff, rbuff )
        self.unselect()
        self.select()
        #print('1. XMT:', binascii.hexlify(xbuff), 'RCV:', binascii.hexlify(rbuff))
        xbuff = bytearray(b'\x12\x34\x56')
        rbuff = bytearray(3)
        self.spi.write_readinto( xbuff, rbuff )
        loopback = int.from_bytes( rbuff, 'big') >> 4
        #print('2. XMT:', binascii.hexlify(xbuff), 'RCV:', binascii.hexlify(rbuff))
        #print('3. CMD:', hex(command), 'LOOPBACK:', hex(loopback) )
        mismatch = command != loopback
        #checks.append( [ hex(command), hex(loopback) ] )
        checks.append( [ mismatch, self.cmd_parse(command), self.cmd_parse(loopback) ] )

    return any( [ c[0] for c in checks ] ), checks

  def select(self):
    self.ss.value(True)
    return self.ss.value()

  def unselect(self):
    self.ss.value(False)
    return self.ss.value()

  def operate(self):
    self.shdn.value(False)
    return self.shdn.value()

  def shutdown(self):
    self.shdn.value(True)
    return self.shdn.value()

  def reset(self):
    self.rst.value(True)
    utime.sleep_ms(1)
    self.rst.value(False)
    utime.sleep_ms(1)

