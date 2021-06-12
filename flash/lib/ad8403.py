""" Analog Devices AD840x Digipot Class

This module is used to write to a one or more Analog Devices
AD840x Digipots over SPI. If more than one Digipot, they are
connected in a daisy chain as described in the datasheet.


Each Digipot has one 10-bit register, composed as follows:
  * 2-bits Address, [ A1, A0 ]  b9 -- b8
  * 8-bits Data,  [ D7 -- D0 ]  b7 -- b0
  * serially send MSB first

## Control pins

Although other connections might be possible, this module 
assumes that the control signals are tied together.

  /SHDN   Shutdown, Rwa open, Rwb shorted
  /RS     Reset all wipers to 0x80 counts
  /SS     Chip Select

## Note about SPI communications with Digipots

Due to some limitations of the SPI implementation in Micropython,
especially for the RP2 (and others?), it's not straightforward to send
an arbitrary number of bits, such as 10 or 20. Instead of wrestling with
the SPI driver to make it work correctly for 10 or 20 bits, we will send
an integer number of bytes and just throw away any remainders. In the
case of talking to one Digipot two bytes are send -- three digipots, 3
bytes, etc.

  * 6 dummy bits +   10 bits  ==  2 bytes (one digipot)
  * 4 dummy bits + 2*10 bits  ==  3 bytes (two digipots)

The code down below in function Digichain.send() used to transmit 
wiper data over SPI requires some explanation.

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

"""

import binascii
from machine import I2C, SPI, Pin, Signal
import utime

# Each Digipot has one 10-bit register, composed as follows:
#   * 2-bits Address, [ A1, A0 ]  b9 -- b8
#   * 8-bits Data,  [ D7 -- D0 ]  b7 -- b0

R1 = 0
R2 = 1
CH1 = 0
CH2 = 1
CH3 = 2
CH4 = 3
CH_ALL = None



'''
'''
class Digichain:

  def __init__(self, spi=0, baudrate=100_000, digipots=[],
              pin_ss = 5, pin_shdn = 27, pin_rst = 26,
              firstbit = SPI.MSB, polarity = 0, phase = 1,
              pin_sck = 6, pin_mosi = 7, pin_miso = 4,
              ):

    self.digipots = digipots
    self.npots = len(digipots)

    self.spi = SPI(spi, baudrate=baudrate, 
                  # firstbit = firstbit,
                  # polarity=polarity, phase=phase, 
                  # sck=Pin(pin_sck), 
                  # mosi=Pin(pin_mosi),
                  # miso=Pin(pin_miso)
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
    Pin( pin_miso, None, pull = Pin.PULL_UP )

    #print('SPI engine initialized')
    #print('Pin  sck:', Pin(pin_sck))
    #print('Pin mosi:', Pin(pin_mosi))
    #print('Pin miso:', Pin(pin_miso))
    
    self.ss_pin = Pin(pin_ss, Pin.OUT, value=1)
    self.ss = Signal(self.ss_pin, invert=True)
    self.shdn_pin = Pin(pin_shdn, Pin.OUT, value=1) 
    self.shdn = Signal(self.shdn_pin, invert=True)
    self.rst_pin = Pin(pin_rst, Pin.OUT, value=1) 
    self.rst = Signal(self.rst_pin, invert=True)
    
    self.verbose = True

    self.operate()
    self.select()
    self.reset()


  def status(self):
    print( 'select:', self.ss.value(), 
           'shutdown:', self.shdn.value(), 
           'reset:', self.rst.value() 
         )
    
  def send( self, channels=None ):
    """send values to specified channel(s), all digipots in chain."""
    
    errs = []
    checks = []
    for c in self.digipots[0].get_channel_list(channels):      
      # build the combined command word
      command = 0
      for dp in self.digipots:
        command  =  command << 10
        command += (dp.cmds[c] & 0x3ff)
      # calculate it's size in bytes a big integer
      # note remaining bits to discard on loopback
      nbits = self.npots * 10
      nbytes = (nbits + 7 ) // 8
      nremainder = 8*nbytes - nbits 
      xbuff = bytearray( command.to_bytes(nbytes, 'big'))
      rbuff = bytearray(bytes(b'\xaa')*nbytes)
      self.spi.write_readinto( xbuff, rbuff )
      self.unselect()
      self.select()
      #print('1. XMT:', binascii.hexlify(xbuff), 'RCV:', binascii.hexlify(rbuff))
      xbuff = bytearray(bytes(b'\x55')*nbytes)
      rbuff = bytearray(nbytes)
      self.spi.write_readinto( xbuff, rbuff )
      loopback = int.from_bytes( rbuff, 'big') >> nremainder
      #print('2. XMT:', binascii.hexlify(xbuff), 'RCV:', binascii.hexlify(rbuff))
      #print('3. CMD:', hex(command), 'LOOPBACK:', hex(loopback) )
      mismatch = command != loopback
      checks.append( [ hex(command), hex(loopback) ] )
      #checks.append( [ mismatch, self.cmd_parse(command), self.cmd_parse(loopback) ] )

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


class Digipot:

  PARALLEL = 1111
  SERIES = 8888
  RWA = 0xaaaa
  RWB = 0xbbbb

  def __init__( self, nchans=4, rtotal=1000, rwiper=0 ): 
    """Analog Devices AD840x Digipot Class

    The Digipot class represents the values and provides calculations
    related to the an AD840x digital potentiometer. Digipots in this 
    family can have one, two, or four potentiometers in a single chip.

      * AD8400 ==  1 pot
      * AD8402 ==  2 pots
      * AD8403 ==  4 pots

    Each potentiometer has three terminals, A, B, and W (wiper).
    The directional sense of resitance vs. counts is

      * Value of 0x00:  R.WB = 0 ohms,  R.WA = Maximum
      * Value of 0xFF:  R.WB = Maximum, R.WB = 0 ohms

    Each of the three Digipots (single, dual, quad) are available 
    with the following total resistances:

      * 1 Kohm
      * 10 Kohm
      * 50 Kohm
      * 100 Kohm

    The formula for resistance vs counts is:

      *  Rwb  = Rwiper + Rtotal * (counts / 256)
      *  Rwa  = Rwiper + Rtotal * ((256 - counts) / 256)
    """

    self.Rtotal = rtotal
    self.Rwiper = rwiper
    self.nchans = nchans
    # vals stores the digipot wiper counts, 0 to 255
    self.vals = [0x80] * self.nchans
    # cmds stores the corresponding 10-bit commands
    self.cmds = [0x080] * self.nchans
    for ch in range(self.nchans):
      self.cmds[ch] += ch << 8
    # rwa and rwb stores the digipot resistances
    self.rwa = [0] * self.nchans
    self.rwb = [0] * self.nchans
    self.ohms()  # populate the lists
    self.verbose = False

  def status(self):
    #print( 'cmds:', ['0x'+hex(c)[2:].zfill(3) for c in self.cmds ] )
    #print( 'vals:', ['0x'+hex(v)[2:].zfill(2) for v in self.vals ] )
    print( 'cmds:', [hex(c) for c in self.cmds ] )
    print( 'vals:', [hex(v) for v in self.vals ] )
    print( 'vals:', self.vals )
    print( 'ohms.Rwa:', self.rwa )
    print( 'ohms.Rwb:', self.rwb )
    print( 'combined:', self.Rcombine() )

  def cmd_parse(self, cmd):
    """Extracts channel and wiper value from a 10-bit command."""
    chan = (cmd & 0x200) >> 8
    val = cmd & 0xff
    return 'w'+str(chan)+'.v'+str(value)

  def get_channel_list(self, channels):
    """Utility function which handles parsing of the channel parameter.
    
    Allowed formats for specifying one or a group of channels:
      * integer     single channel       e.g.:   1
      * list        list of channels     e.g.:   [0,3] 
      * #channels   all the channels     e.g.:   4
      * None        all the channels
    These three examples would evaluate to the following, respectively,
    for quad Digipots:
      * [ 1 ]
      * [ 0, 3 ]
      * [ 0, 1, 2, 3 ]
      * [ 0, 1, 2, 3 ]
    Channel values out of range are silently discarded
    """
    clist = []
    if channels is None:
      clist = [ c for c in range(self.nchans) ]
    elif type(channels) is int:
      if channels == self.nchans: # all channels
        clist = [ c for c in range(self.nchans) ]
      else:
        clist = [ channels ]
    elif type(channels) is list:
      clist = channels
    # check the values, only return in-bounds ones
    return [ c for c in clist if c >= 0 and c < self.nchans ]

  def counts(self, value, channels=None ):
    """Sets wiper value(s) and 10-bit SPI command(s) for the reqested channels."""
    for chan in self.get_channel_list(channels):
      command = chan << 8
      command += (value & 0xff)
      self.vals[chan] = value
      self.cmds[chan] = command
    self.ohms() # update the resistances
    # temporary, show combined
    # print( self.Rcombine()[0], self.vals )
    if self.verbose:
      self.status()
        
  # TODO make reverse function, given ohms calculate values
  def ohms(self):
    """Calculates the resistance of all channels."""
    #   Rwb  = Rwiper + Rtotal * (counts / 256)
    #   Rwa  = Rwiper + Rtotal * ((256 - counts) / 256)
    g = 0
    rtotal=0.0
    reach=[]
    for chan in self.get_channel_list(self.nchans):
      self.rwa[chan]  = float( 256 - self.vals[chan] ) / 256.0
      self.rwb[chan]  = float( self.vals[chan] ) / 256.0
      self.rwa[chan] *= self.Rtotal
      self.rwb[chan] *= self.Rtotal 
      self.rwa[chan] += self.Rwiper
      self.rwb[chan] += self.Rwiper

  def Rcombine(self, channels=None, 
               connection=PARALLEL, terminal=RWB):
    """Combined ohms for specified channel(s), connection, and terminals."""
    # This calculates all combinations of series and parallel connections
    # on both possible terminal connections, Rwa and Rwb.
    # At the end, it provides the requested answer.
    # Could be modified to return multiple answers
    # Only alows simple combinations, such as
    #   N channels in parallel or series.
    # Complicated connections like:
    #   R1wa + ( R2wa || R3wa || R0wb )
    # are not supported.
    series_rwa = 0.0
    series_rwb = 0.0
    gwa = 0.0
    gwb = 0.0
    zero_wa = False
    zero_wb = False
    rlist_rwa = []
    rlist_rwb = []
    for chan in self.get_channel_list(channels):
      rlist_rwa.extend( [ self.rwa[chan] ] )
      rlist_rwb.extend( [ self.rwb[chan] ] )
      series_rwa += self.rwa[chan]
      series_rwb += self.rwb[chan]
      if self.rwa[chan] == 0: zero_wa = True
      else: gwa += 1.0 / self.rwa[chan]
      if self.rwb[chan] == 0: zero_wb = True
      else: gwb += 1.0 / self.rwb[chan]
    if zero_wa: parallel_rwa = 0.0
    else: parallel_rwa = 1.0 / gwa
    if zero_wb: parallel_rwb = 0.0
    else: parallel_rwb = 1.0 / gwb

    if self.verbose:
      print( series_rwa, parallel_rwa, rlist_rwa )
      print( series_rwb, parallel_rwb, rlist_rwb )

    retval = []
    if connection == self.PARALLEL:
      if terminal == self.RWA: retval.extend( [ parallel_rwa ] )
      if terminal == self.RWB: retval.extend( [ parallel_rwb ] )
    if connection == self.SERIES:
      if terminal == self.RWA: retval.extend( [ series_rwa ] )
      if terminal == self.RWB: retval.extend( [ series_rwb ] )
    return retval

####    dp = Digipot()
####    #dp.status()
####    #dp.counts(0)
####    #dp.counts(255)
####    
####    for val in range(25):
####      dp.counts(val)
####      ohms = dp.Rcombine()[0]
####      print( f'{val}\t{ohms:.2f}' )


