import gc
from inverse import Registers, Inverse

gc.collect()
cal1 = Inverse('data/invert-sn0-r1-cal.dat')
gc.collect()
cal2 = Inverse('data/invert-sn0-r2-cal.dat')
gc.collect()
