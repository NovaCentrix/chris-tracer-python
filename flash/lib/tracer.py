import gc
gc.collect()
import ad8403
gc.collect()
from machine import I2C, SPI, Pin, Signal
gc.collect()
import ssd1306
gc.collect()
import utime
gc.collect()

# Shunting Relays
# K1 shorts Digipot R1, K2 shorts R2
class Relay:
  def __init__(self, pinnum, relayid=''):
    self.relayid = relayid
    self.pinnum = pinnum
    self.pin = Pin(self.pinnum, Pin.OUT, value=0) 
    self.sig = Signal(self.pin, invert=False)

  def shunt(self):
    self.sig.value(True)
        
  def open(self):
    self.sig.value(False)

  def set(self, value):
    self.sig.value(value)

  def get(self):
    return self.sig.value() == 1
        
  def get_string(self):
    if self.sig.value(): return 'shunt'
    else: return 'open'

class TraceR:

  def __init__(self):

    self.i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    self.disp = ssd1306.SSD1306_I2C(64, 32, self.i2c)

    # initialize the Digipot chain
    self.r1 = ad8403.Digipot(chipid='1')
    self.r2 = ad8403.Digipot(chipid='2')
    self.pots = [ self.r1, self.r2 ]
    self.chain = ad8403.Digichain(digipots=self.pots)
    
    # pixel offsets for the each of the text rows and data fields
    # from above, this display is 32 pixels tall x 64 pixels wide
    self.disp_rows = [2, 15]
    self.disp_tabs = [2, 32]

    # === Shunting Relays ===
    # K1 shorts Digipot R1, K2 shorts R2
    self.k1 = Relay(29, relayid='1')
    self.k2 = Relay(28, relayid='2')
    self.relays = [self.k1, self.k2]

  def display_resistances_update(self):
    """Update resistance values on screen."""
    r1str = str(int(self.r1.Rcombine()[0]+0.5))
    r2str = str(int(self.r2.Rcombine()[0]+0.5))
    self.disp.fill(0)
    self.disp.text("R1=", self.disp_tabs[0], self.disp_rows[0])
    self.disp.text(r1str, self.disp_tabs[1], self.disp_rows[0])
    self.disp.text("R2=", self.disp_tabs[0], self.disp_rows[1])
    self.disp.text(r2str, self.disp_tabs[1], self.disp_rows[1])
    self.disp.show()
  
  def display_counts_update(self):
    """Update digipot counts values on screen."""
    # NOTE: current all counts are the same
    # so fetching val[0] is representative of the pot
    r1str = str(self.r1.vals[0])
    r2str = str(self.r2.vals[1])
    if self.k1.get(): r1str+='*'
    if self.k2.get(): r2str+='*'
    self.disp.fill(0)
    self.disp.text("X1=", self.disp_tabs[0], self.disp_rows[0])
    self.disp.text(r1str, self.disp_tabs[1], self.disp_rows[0])
    self.disp.text("X2=", self.disp_tabs[0], self.disp_rows[1])
    self.disp.text(r2str, self.disp_tabs[1], self.disp_rows[1])
    self.disp.show()

  def display_ohms_update(self):
    """Update digipot counts values on screen."""
    # NOTE: current all counts are the same
    # so fetching val[0] is representative of the pot
    if self.r1.cal is not None:
      r1str = str(int(self.r1.cal.rnom))
    else:
      r1str = 'unk'
    if self.r2.cal is not None:
      r2str = str(int(self.r2.cal.rnom))
    else:
      r2str = 'unk'
    if self.k1.get(): r1str+='*'
    if self.k2.get(): r2str+='*'
    self.disp.fill(0)
    self.disp.text("R1=", self.disp_tabs[0], self.disp_rows[0])
    self.disp.text(r1str, self.disp_tabs[1], self.disp_rows[0])
    self.disp.text("R2=", self.disp_tabs[0], self.disp_rows[1])
    self.disp.text(r2str, self.disp_tabs[1], self.disp_rows[1])
    self.disp.show()

  def display_splash_screen(self, serno):
    """Welcome screen."""
    self.disp.text("Welcome", 2,1)
    self.disp.text("TraceR", 2,11)
    self.disp.text(serno, 2,21)
    self.disp.show()

#### def testme():
####   tr = TraceR()
####   tr.display_splash_screen()
####   utime.sleep(3) # wait three seconds
####   tr.display_resistances_update()

