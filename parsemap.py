#! /usr/bin/python
"""
Parse Ultima VI map files, and output them in some different format.

Usage: parsemap.py COMMAND[...]

COMMANDS:
  writejs         Write the map data as Javascript code
  choptiles       Chop tiles out of grid of them
  composechunks   Print shell commands to combine tiles into 1024 chunks
  composemap      Commands to combine the 32K chunks into a single huge image
  composedungeons Commands to make images of the 5 dungeon levels

PREREQUITES:
  Ultima VI files "chunks" and "map" are expected to be found in ./Ultima6/
  ImageMagick is needed to compose the images
  An image of the U6 tiles http://www.reenigne.org/computer/u6maps/u6tiles.png

ALSO:
  The compose* commands generate shell commands that call
  ImageMagick's convert to stick the tiles together, so pipe the
  output into bash (e.g.) to actually do something

  This command would generate the world and dungeon maps:
  $ parsemap.py choptiles composechunks composemap componsedungeons | bash

ABOUT THE U6 MAP:
  The file "chunks" contains 1024 8x8 byte arrays giving tile indices.
  These consititute the building blocks of which the map is composed.
  
  The file "map" contains the world map, stored as an 8x8 array of
  16x16 arrays of indices into the set of chunks. Each index occupies
  3 nibbles, each pair of which is stored with the nibbles permuted
  strangely. The world map is followed by 5 dungeons, which are 32x32
  arrays of chunk indices.

  This same program should be able to decode the Savage Empire and
  Martian Dreams maps.

  There's also a bunch of objects to overlay on the map but I don't
  know how to do that yet.
"""

# Related sites
# http://www.reenigne.org/computer/u6maps/index.html
# http://www.graf.torun.pl/~rackne/u6like.html
# http://ian-albert.com/misc/ultima6maps.php

import os, sys, struct, getopt

def readchunk(file):
  return [list(struct.unpack('8B', file.read(8))) for row in range(8)]

def readchunks(f):
  return [readchunk(f) for chunk in range(1024)]

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
  # u6tiles came from http://www.reenigne.org/computer/u6maps/u6tiles.png
  print "mkdir -p tiles"
  n = 0
  for y in range(32):
    for x in range(8):
      print 'convert -crop 16x16+%d+%d u6tiles.png tiles/tile%03d.png' % \
            (x*16, y*16, n)
      n += 1


def composechunks(chunks):
  print "mkdir -p chunks"
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
  # This takes around 2GB of memory, so may cause lots of swapping and
  # take a good long while. Final result is a 50MB 16384x16394 image
  print "mkdir -p compositions"
  print "convert",
  for row in map:
    print "\\( +append", 
    for chunk in row:
      print "chunks/chunk%04d.png" % chunk,
    print "\\)",
  print "-append compositions/wholebigmap.png"


def composedungeons(dungeons):
  # Dungeon images are around 3MB, 4096x4096
  print "mkdir -p compositions"
  for d in range(5):
    dungeon = dungeons[d]
    print "convert",
    for row in dungeon:
      print "\\( +append", 
      for chunk in row:
        print "chunks/chunk%04d.png" % chunk,
      print "\\)",
    print "-append compositions/dungeon%d.png" % d



def writejs(map, dungeons, chunks):
  print "var map = [";
  for row in map:
    print ' ', row, ','
  print '  ];'

  for dungeon in range(5):
    print "var dungeon%d = [" % dungeon
    for row in dungeons[dungeon]:
      print ' ', row, ','
    print '  ];';

  print "var chunks = [",
  for chunk in chunks:
    print ' ', chunk, ','
  print "  ];";


if __name__ == "__main__":
  main()
