#!/usr/bin/env python

import sys

class Registers:
  def __init__( self, rnom, ract, rerr, regs ):
    self.rnom = rnom
    self.ract = ract
    self.rerr = rerr
    self.regs = regs
  def __str__(self):
    return '{rnom:.1f}\t'\
           '{regs0}\t{regs1}\t{regs2}\t{regs3}\t'\
           '{ract:.3f}\t{rerr:+.3f}'\
           .format(rnom=self.rnom, regs0=self.regs[0], regs1=self.regs[1],
               regs2=self.regs[2], regs3=self.regs[3], ract=self.ract,
               rerr=self.rerr )
  def __repr__(self):
    return '{rnom:.1f}\t'\
           '{regs0}\t{regs1}\t{regs2}\t{regs3}\t'\
           '{ract:.3f}\t{rerr:+.3f}'\
           .format(rnom=self.rnom, regs0=self.regs[0], regs1=self.regs[1],
               regs2=self.regs[2], regs3=self.regs[3], ract=self.ract,
               rerr=self.rerr )

class Inverse:
  def __init__(self, fname=None):
    self.initialized = False
    self.regs=[]
    self.serno = None
    self.resno = None
    self.rbeg = None
    self.rend = None
    self.nres = None
    if fname is not None:
      self.load(fname)

  def load(self, fname):
    try:
      with open(fname, 'r') as fin:
        npoints=0
        for line in fin:
          row = line.strip().split('\t')
          #print(type(row), len(row), row)
          if row[0][0] == '#': continue
          if self.serno is None:
            self.serno = row[0]
          elif self.resno is None:
            self.resno = row[0]
          elif self.rbeg is None:
            self.rbeg = float(row[0])
          elif self.rend is None:
            self.rend = float(row[0])
          elif self.nres is None:
            self.nres = int(row[0])
          else:
            rnom = float(row[0])
            regs=[]
            regs.append( int(row[1]) )
            regs.append( int(row[2]) )
            regs.append( int(row[3]) )
            regs.append( int(row[4]) )
            ract = float(row[5])
            rerr = float(row[6])
            self.regs.append(Registers(rnom, ract, rerr, regs))
      self.initialized = True
    except OSError as error:
      self.initialized = False

  def print_header( self ):
    print('{serno}\t# serial number'.format(serno=self.serno))
    print('{resno}\t# resistor number'.format(resno=self.resno))
    print('{rbeg}\t# minimum resistance value'.format(rbeg=self.rbeg))
    print('{rend}\t# maximum resistance value'.format(rend=self.rend))
    print('{nres}\t# number of resistances'.format(nres=self.nres))

  def print_regs( self ):
    print('# Rnominal, Registers[1-4], Ractual, Rerror')
    for reg in self.regs:
      print(reg, file=fp)

  def print_all( self ):
    self.print_header(fp)
    self.print_regs(fp)

  def lookup( self, rnom ):
    irnom = int(rnom+0.5)
    if irnom < int(self.rbeg):
      return self.regs[1]
    if irnom > int(self.rend):
      return self.regs[-1]
    match = False
    for regs in self.regs:
      if irnom == int(regs.rnom):
        match = True
        break
    if match:
      return regs
    else:
      return None
