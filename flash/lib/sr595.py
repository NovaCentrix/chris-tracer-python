# Simple 595 Shift Regsiter Class
from machine import I2C, SPI, Pin, Signal
import utime

class SR:

  def __init__(self):
    self.spi = SPI(0, baudrate=100_000, 
                  # firstbit = SPI.MSB,
                   #polarity=0, phase=1, 
                   #sck=Pin(6), mosi=Pin(7), miso=Pin(4)
               )

    self.oena_pin = Pin(5, Pin.OUT, value=1)
    self.oena = Signal(self.oena_pin, invert=True)
    self.xfer_pin = Pin(27, Pin.OUT, value=1) #A0
    self.xfer = Signal(self.xfer_pin, invert=False)
    self.mrst_pin = Pin(26, Pin.OUT, value=1) #A1
    self.mrst = Signal(self.mrst_pin, invert=True)

    self.master_reset()
    self.transfer()
    self.enable()

  def show_status(self):
    print( 'oena:', self.oena.value(), 
           'xfer:', self.xfer.value(), 
           'mrst:', self.mrst.value() )


# Bit reverse an 8 bit value
  def rbit8(self,v):
      v = (v & 0x0f) << 4 | (v & 0xf0) >> 4
      v = (v & 0x33) << 2 | (v & 0xcc) >> 2
      return (v & 0x55) << 1 | (v & 0xaa) >> 1

  # inverts and reverses bits
  def invert(self, buff):
    ibuff = bytearray()
    for v in buff:
      ibuff.append( 0xff ^ v )
    return ibuff

  def backwards(self, buff):
    ibuff = bytearray()
    for v in buff:
      ibuff.append( self.rbit8(v) )
    return ibuff

  def send_buff(self, buff):
    self.spi.write( self.invert( self.backwards(buff) ) )
    self.transfer()

  def send_int(self, val):
    val8 = val % 256
    self.send_buff(bytearray(val8.to_bytes(1,'little')))

  def enable(self):
    self.oena.value(True)
    return self.oena.value()

  def disable(self):
    self.oena.value(False)
    return self.oena.value()

  def transfer(self):
    self.xfer.value(True)
    utime.sleep_ms(1)
    self.xfer.value(False)
    utime.sleep_ms(1)

  def master_reset(self):
    self.mrst.value(True) # come out of reset
    utime.sleep_ms(1)
    self.mrst.value(False) # come out of reset
    utime.sleep_ms(1)
