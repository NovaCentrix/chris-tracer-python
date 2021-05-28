import time
import sys
import select

def run():
  print('running...')
  while True:        
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:        
      ch = sys.stdin.read(1)
      # print(hex(ord(ch)))
      if (ch == 'a'):
        # 100 characters
        print( 'a'*100 )

