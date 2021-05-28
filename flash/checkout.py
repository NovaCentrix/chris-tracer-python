# Proof of concept: Tiny 2040 + 0.49 in OLED + Shift Register

from machine import I2C, SPI, Pin, Signal
import ssd1306

class ShiftRegister595:
  def _init_(self):
    self.spi = SPI(0, baudrate=100000, 
               polarity=1, phase=1, 
               sck=Pin(6), mosi=Pin(7), miso=Pin(4))
    self.oena_pin = Pin(5, Pin.OUT, value=1)
    self.oena = Signal(oena_pin, invert=True)
    self.xfer_pin = Pin(27, Pin.OUT, value=1) #A0
    self.xfer = Signal(xfer_pin, invert=False)
    self.mrst_pin = Pin(26, Pin.OUT, value=1) #A1
    self.mrst = Signal(mrst_pin, invert=True)
  def print(self):
    print( 'oena:', self.oena.value(), 
           'xfer:', self.xfer.value(), 
           'mrst:', self.mrst.value() )
  def write(self, buff):
    self.spi.write(buff)


i2c = I2C(0, scl=Pin(1), sda=Pin(0))
disp = ssd1306.SSD1306_I2C(64, 32, i2c)

disp.text("Chris", 2,2)
disp.show()
bbb = bytearray( b'0x55aa55aa')
#print(bbb)

#sr = ShiftRegister595()
#sr.write(bbb)
  
