#! /usr/bin/python
"""
Parse Ultima VI map files, and output them in some different format.
Usage: parsemap.py COMMAND[...]
COMMANDS:
  writejs        Write the map data as Javascript code
  choptiles      Chop tiles out of grid of them
  composechunks  Print shell commands to combine tiles into 1024 chunks
  composemap     Commands to combine the 32K chunks into a single huge image
Prerequites:
  Ultima VI files "chunks" and "map" are expected to be found at ./Ultima6
  ImageMagick to compose the images
  Image of the U6 tiles http://www.reenigne.org/computer/u6maps/u6tiles.png
"""
import os, sys, struct, getopt

def readchunk(file):
  return [list(struct.unpack('8B', file.read(8))) for row in range(8)]

def readchunks(f):
  return [readchunk(f) for chunk in range(1024)]

def hi_nibble(b):
  return b / 16

def lo_nibble(b):
  return b % 16

def tri_nibble(hi, med, lo):
  return hi * 256 + med * 16 + lo

def readsuperchunkrow(f, size):
  result = []
  for pair in range(size / 2):
    data = struct.unpack('3B', f.read(3))  # 3 nibbles per chunk num
    result.append(256 * (data[1] % 16) + data[0])
    result.append( 16 * data[2] + (data[1] / 16));
  return result

def readsuperchunk(f):
  return [readsuperchunkrow(f, 16) for row in range(16)]

def readmap(f):
  return [[readsuperchunk(f) for x in range(8)]
          for y in range(8)]

def readdungeon(f):
  return [readsuperchunkrow(f, 32) for row in range(32)]

def flattenmap(m):
  result = []
  for superrow in m:
    for r in range(len(superrow)):
      row = []
      for superchunk in superrow:
        row.extend(superchunk[r])
      result.append(row)
  return result

def usage():
  print __doc__
  sys.exit()

def main():
  opts,args = getopt.getopt(sys.argv[1:], '')

  mapf = open('Ultima6/map', 'rb')
  map = flattenmap(readmap(mapf))
  dungeons = [readdungeon(mapf) for level in range(5)]
  chunks = readchunks(open('Ultima6/chunks', 'rb'))

  if not args: usage()
  for a in args:
    if a == 'writejs':
      writejs(map, dungeons, chunks)
    elif a == 'choptiles':
      choptiles()
    elif a == 'composechunks':
      composechunks(chunks)
    elif a == 'composemap':
      composemap(map)
    elif a == 'composedungeons':
      composedungeons(dungeons)
    else:
      usage()

def choptiles():
  n = 0
  for y in range(32):
    for x in range(8):
      print 'convert -crop 16x16+%d+%d u6tiles.png tiles/tile%03d.png' % \
            (x*16, y*16, n)
      n += 1


def composechunks(chunks):
  n = 0
  for chunk in chunks:
    print "convert",
    for row in chunk:
      print "\\( +append", 
      for tile in row:
        print "tiles/tile%03d.png" % tile,
      print "\\)",
    print "-append chunks/chunk%04d.png" % n
    n += 1

def composemap(map):
  print "convert",
  for row in map:
    print "\\( +append", 
    for chunk in row:
      print "chunks/chunk%04d.png" % chunk,
    print "\\)",
  print "-append wholebigmap.png"


def composedungeons(dungeons):
  for d in range(5):
    dungeon = dungeons[d]
    print "convert",
    for row in dungeon:
      print "\\( +append", 
      for chunk in row:
        print "chunks/chunk%04d.png" % chunk,
      print "\\)",
    print "-append dungeon%d.png" % d



def writejs(map, dungeons, chunks):
  '''
  print "var map = [";
  for row in map:
    print ' ', row, ','
  print '  ];'
  '''

  for dungeon in range(5):
    print "var dungeon%d = [" % dungeon
    for row in dungeons[dungeon]:
      print ' ', row, ','
    print '  ];';

  '''
  print "var chunks = [",
  for chunk in chunks:
    print ' ', chunk, ','
  print "  ];";
  '''

if __name__ == "__main__":
  main()
