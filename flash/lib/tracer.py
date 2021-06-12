from machine import I2C, SPI, Pin, Signal
import ssd1306
import ad840x
import utime

class TraceR:

  def __init__(self):

    # === Display ===
    # Note: could make this a class unto itself,
    # if this TraceR class becomes too cluttered
    self.i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    self.disp = ssd1306.SSD1306_I2C(64, 32, self.i2c)
    self.disp.text("Welcome", 2,1)
    self.disp.text("to the", 2,11)
    self.disp.text("TraceR", 2,21)
    self.disp.show()
    # pixel offsets for the each of the text rows and data fields
    # from above, this display is 32 pixels tall x 64 pixels wide
    self.disp_rows = [2, 15]
    self.disp_tabs = [2, 32]

    # === Digipots ===
    # R1 is on the MCU side of the board
    # R2 is on the Display side of the board
    self.pot = ad840x.Digipot()
    self.pot.counts(0xc0, 0)
    self.pot.counts(0x40, 1)
    self.pot.send()

    # === Shunting Relays ===
    # K1 shorts Digipot R1, K2 shorts R2
    self.relay1_pin = Pin(29, Pin.OUT, value=0) 
    self.relay1 = Signal(self.relay1_pin, invert=False)
    self.relay2_pin = Pin(28, Pin.OUT, value=0) 
    self.relay2 = Signal(self.relay2_pin, invert=False)

  def short(self, channel):
    if channel == 0:
        self.relay1.value(True)
    if channel == 1:
        self.relay2.value(True)
        
  def open(self, channel):
    if channel == 0:
        self.relay1.value(False)
    if channel == 1:
        self.relay2.value(False)
        



# pot.ohms(0,0xc0)
# pot.ohms(1,0x40)
# pot.send()
# 
# disp.fill(0)
# disp.text("R1=", 2,2)
# disp.text(str(100), 32,2)
# disp.text("R2=", 2,15)
# disp.text(str(220), 32,15)
# disp.show()
# 
# #for _ in range(1000):
# #    pot.set_ohms(0, 128)
# #    pot.set_ohms(1, 128)
# #    pot.set_ohms(2, 128)
# #    pot.set_ohms(3, 128)
# 
# pot.show_status()
# 
# # for i in range(100):
# #   print(i)
# #   disp.fill(0)
# #   disp.text(str(i), 2,2)
# #   disp.show()
# #   sr.send_int(i)
# #   utime.sleep_ms(1000)

