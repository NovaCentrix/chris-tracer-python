#!/usr/bin/env python3

''' Analog Devices AD840x Digipot Class

Basic description, SPI registers:

There is one 10-bit register, composed as follows:
  * 2-bits Address, [ A1, A0 ]
  * 8-bits Data,  [ D7 -- D0 ]

Digipots in this family may have up to four in a single chip
  * Value of 0x00:  R.WB = 0 ohms,  R.WA = Maximum
  * Value of 0xFF:  R.WB = Maximum, R.WB = 0 ohms

Control pins (hardcoded for now):
  /SHDN  GP27
  /RS    GP36
  /SS    GP5 '''

class Digipot:

  def __init__(self):
    self.channel = 4

# Bit reverse an 8 bit value
  def rbit8(self,v):
      v = (v & 0x0f) << 4 | (v & 0xf0) >> 4
      v = (v & 0x33) << 2 | (v & 0xcc) >> 2
      return (v & 0x55) << 1 | (v & 0xaa) >> 1

# inverts bits
  def invert(self, buff):
    ibuff = bytearray()
    for v in buff:
      ibuff.append( 0xff ^ v )
    return ibuff

# reverses bits
  def backwards(self, buff):
    ibuff = bytearray()
    for v in buff:
      ibuff.append( self.rbit8(v) )
    return ibuff

  def send_value(self, channel, value):
    # instead of wrangling the SPI driver to send 10 or 20 bits
    # we will send an integer number of bytes and just throw away
    # any remainders
    command = (channel & 0x3) << 8
    command += (value & 0xff)
    buff = bytearray( command.to_bytes(2, 'big'))
    return buff


pot = Digipot()

buff = pot.send_value( 3, 33 )
print(buff.hex())

