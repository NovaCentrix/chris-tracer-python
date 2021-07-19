import gc
gc.collect()
import binascii
gc.collect()
from machine import I2C, SPI, Pin, Signal
gc.collect()
import utime
gc.collect()

# Each Digipot has one 10-bit register, composed as follows:
#   * 2-bits Address, [ A1, A0 ]  b9 -- b8
#   * 8-bits Data,  [ D7 -- D0 ]  b7 -- b0

#R1 = 0
#R2 = 1
#CH1 = 0
#CH2 = 1
#CH3 = 2
#CH4 = 3
#CH_ALL = None

class Digipot:

  PARALLEL = 1111
  SERIES = 8888
  RWA = 0xaaaa
  RWB = 0xbbbb

  def __init__( self, nchans=4, rtotal=1000, rwiper=50, chipid='' ): 
    self.chipid = chipid
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
    self.cal = None # cal for current setting, when available
    self.ohms()  # populate the lists
    self.verbose = False

  def status(self):
    print('status')
    #### #print( 'cmds:', ['0x'+hex(c)[2:].zfill(3) for c in self.cmds ] )
    #### #print( 'vals:', ['0x'+hex(v)[2:].zfill(2) for v in self.vals ] )
    #### print( 'cmds:', [hex(c) for c in self.cmds ] )
    #### print( 'vals:', [hex(v) for v in self.vals ] )
    #### print( 'vals:', self.vals )
    #### print( 'ohms.Rwa:', self.rwa )
    #### print( 'ohms.Rwb:', self.rwb )
    #### print( 'combined:', self.Rcombine() )

  def cmd_parse(self, cmd):
    """Extracts channel and wiper value from a 10-bit command."""
    chan = (cmd & 0x200) >> 8
    val = cmd & 0xff
    return 'w'+str(chan)+'.v'+str(value)

  def get_channel_list(self, channels):
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

  def counts(self, values, channels=None ):
    """Sets wiper value(s) and 10-bit SPI command(s) for the reqested channels."""
    if not isinstance( values, list ):
      # only one value is given
      values = [ values ] * self.nchans
    for chan in self.get_channel_list(channels):
      command = chan << 8
      command += (values[chan] & 0xff)
      self.vals[chan] = values[chan]
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
    return [ self.rwa[0]/4.0 ]

####   def Rcombine(self, channels=None, 
####                connection=PARALLEL, terminal=RWB):
####     """Combined ohms for specified channel(s), connection, and terminals."""
####     # This calculates all combinations of series and parallel connections
####     # on both possible terminal connections, Rwa and Rwb.
####     # At the end, it provides the requested answer.
####     # Could be modified to return multiple answers
####     # Only alows simple combinations, such as
####     #   N channels in parallel or series.
####     # Complicated connections like:
####     #   R1wa + ( R2wa || R3wa || R0wb )
####     # are not supported.
####     series_rwa = 0.0
####     series_rwb = 0.0
####     gwa = 0.0
####     gwb = 0.0
####     zero_wa = False
####     zero_wb = False
####     rlist_rwa = []
####     rlist_rwb = []
####     for chan in self.get_channel_list(channels):
####       rlist_rwa.extend( [ self.rwa[chan] ] )
####       rlist_rwb.extend( [ self.rwb[chan] ] )
####       series_rwa += self.rwa[chan]
####       series_rwb += self.rwb[chan]
####       if self.rwa[chan] == 0: zero_wa = True
####       else: gwa += 1.0 / self.rwa[chan]
####       if self.rwb[chan] == 0: zero_wb = True
####       else: gwb += 1.0 / self.rwb[chan]
####     if zero_wa: parallel_rwa = 0.0
####     else: parallel_rwa = 1.0 / gwa
####     if zero_wb: parallel_rwb = 0.0
####     else: parallel_rwb = 1.0 / gwb
#### 
####     #### if self.verbose:
####     ####   print( series_rwa, parallel_rwa, rlist_rwa )
####     ####   print( series_rwb, parallel_rwb, rlist_rwb )
#### 
####     retval = []
####     if connection == self.PARALLEL:
####       if terminal == self.RWA: retval.extend( [ parallel_rwa ] )
####       if terminal == self.RWB: retval.extend( [ parallel_rwb ] )
####     if connection == self.SERIES:
####       if terminal == self.RWA: retval.extend( [ series_rwa ] )
####       if terminal == self.RWB: retval.extend( [ series_rwb ] )
####     return retval
#### 




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


####    dp = Digipot()
####    #dp.status()
####    #dp.counts(0)
####    #dp.counts(255)
####    
####    for val in range(25):
####      dp.counts(val)
####      ohms = dp.Rcombine()[0]
####      print( f'{val}\t{ohms:.2f}' )


