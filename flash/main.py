# Proof of concept: Tiny 2040 + 0.49 in OLED + Shift Register

from machine import I2C, SPI, Pin, Signal
import ssd1306
import sr595
import utime

i2c = I2C(0, scl=Pin(1), sda=Pin(0))
disp = ssd1306.SSD1306_I2C(64, 32, i2c)

disp.text("Chris", 2,2)
disp.show()
bbb = bytearray( b'\x55\xaa\x55\xaa')

sr = sr595.SR()
sr.show_status()
sr.send_buff(bbb)

for i in range(100):
  print(i)
  disp.fill(0)
  disp.text(str(i), 2,2)
  disp.show()
  sr.send_int(i)
  utime.sleep_ms(1000)

