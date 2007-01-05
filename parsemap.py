#! /usr/bin/python
# (c) 2007 Eric Fredricksen
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

# TODO: items in containers, esp. eggs not handled right

# Related sites
# http://www.reenigne.org/computer/u6maps/index.html
# http://www.graf.torun.pl/~rackne/u6like.html
# http://ian-albert.com/misc/ultima6maps.php
# http://3e8.org/pub/ultima6/u6notes.txt
# http://3e8.org/hacks/ultima6/

import os, sys, struct, getopt


def readchunk(f):
  # A chunk is an 8x8 array of tile numbers
  return [list(struct.unpack('8B', f.read(8))) for row in range(8)]

def readchunks(f):
  # There are 1024 chunks
  return [readchunk(f) for chunk in range(1024)]

def readsuperchunkrow(f, size):
  # Each row within a superchunk is 16 or 32 3-nibble chunk indices,
  # each adjacent pair of which have the nibbles scrabled weirdly
  result = []
  for pair in range(size / 2):
    data = struct.unpack('3B', f.read(3))  # 3 nibbles per chunk num
    result.append(256 * (data[1] % 16) + data[0])
    result.append( 16 * data[2] + (data[1] / 16));
  return result

def readsuperchunk(f):
  # A superchunk is a 16x16 array of chunk indices
  return [readsuperchunkrow(f, 16) for row in range(16)]

def readmap(f):
  # The world map is an 8x8 array of superchunks
  return [[readsuperchunk(f) for x in range(8)]
          for y in range(8)]

def readdungeon(f):
  # Each dungeon is a 32x32 array of superchunks
  return [readsuperchunkrow(f, 32) for row in range(32)]

def flattenmap(m):
  # Convert the 8x8 array of 16x16 arrays of chunks into a single
  # 128x128 array of chunks
  result = []
  for superrow in m:
    for r in range(len(superrow[0])):
      row = []
      for superchunk in superrow:
        row.extend(superchunk[r])
      result.append(row)
  return result

def readbasetile(f):
  # First tile numbers for each of the 1024 game objects
  return struct.unpack('<1024H', f.read(2048))

def readobjblk(f):
  # SAVEGAME contains one of these for each superchunk and dungeon level.
  # Each starts with a count of entries
  count, = struct.unpack('<H', f.read(2))
  result = {}
  for i in range(count):
    # http://3e8.org/pub/ultima6/u6notes.txt
    (status,h,d1,d2,type,quantity,quality) = struct.unpack('<4BH2B', f.read(8))
    x = (d1 & 0x3) << 8 | h
    y = (d2 & 0xf) << 6 | (d1 >> 2)
    z = (d2 >> 4)
    object = type & 0x3ff
    frame = type >> 10
    on_map = not (status & 0x10)  # else x,y aren't map coords
    coord = y * 1024 + x
    if on_map:
      tile = basetile[object] + frame
      objtile = tile
      for v in range(tileflag[objtile]['vsize']):
        for h in range(tileflag[objtile]['hsize']):
          stack = result.setdefault((y-v) * 1024 + (x-h), [])
          atile = animdata.get(tile,[tile])[0]
          if tileflag[objtile]['ontop'] or v > 0 or h > 0:
            stack.insert(0, tile)
          else:
            stack.append(tile)
          tile -= 1
  return result

def readobjlist(f):
  objlist = {}
  coords = []
  f.seek(0x100)
  for i in range(256):
    h, d1, d2 = struct.unpack("BBB", f.read(3))
    x = (d1 & 0x3) << 8 | h
    y = (d2 & 0xf) << 6 | (d1 >> 2)
    z = (d2 >> 4)
    coords.append(y * 1024 + x)
  for i in range(256):
    type, = struct.unpack("<H", f.read(2))
    object = type & 0x3ff
    frame = type >> 10
    objlist.setdefault(coords[i], []).append(basetile[object]+frame)
  return objlist

def readanimdata(f):
  count, = struct.unpack('<H', f.read(2))
  froms = struct.unpack('<%dH' % count, f.read(2 * count))
  tos = struct.unpack('<%dH' % count, f.read(2 * count))
  ones = struct.unpack('<%dB' % count, f.read(count))
  twos = struct.unpack('<%dB' % count, f.read(count))
  return dict(zip(froms, zip(tos, ones, twos)))


def readtileflag(f):
  flags1 = struct.unpack('2048B', f.read(2048))
  flags2 = struct.unpack('2048B', f.read(2048))
  unknown = f.read(1024)
  flags3 = struct.unpack('2048B', f.read(2048))
  result = []
  for f1,f2,f3 in zip(flags1, flags2, flags3):
    result.append({
      'passable': (f1 & 0x2) == 0,
      'ontop': (f2 & 0x10) != 0,
      'vsize': (f2 & 0x40) and 2 or 1,
      'hsize': (f2 & 0x80) and 2 or 1
      })
  return result


def parse_everything():
  global map, dungeons, chunks, basetile, animdata, objblk, dungblk, objlist
  global tileflag

  mapf = open('Ultima6/MAP', 'rb')
  map = flattenmap(readmap(mapf))
  dungeons = [readdungeon(mapf) for level in range(5)]

  chunks = readchunks(open('Ultima6/CHUNKS', 'rb'))

  tileflag = readtileflag(open('Ultima6/TILEFLAG', 'rb'))

  basetile = readbasetile(open('Ultima6/BASETILE', 'rb'))

  animdata = readanimdata(open('Ultima6/animdata', 'rb'))

  objblk = {}
  for y in 'ABCDEFG':
    for x in 'ABCDEFG':
      blk = readobjblk(open('Ultima6/SAVEGAME/OBJBLK%s%s'%(x,y),'rb'))
      for key,value in blk.iteritems():
        objblk.setdefault(key,[]).extend(value)
  dungblk = [readobjblk(open('Ultima6/SAVEGAME/OBJBLK%sI'%(d), 'rb'))
             for d in 'ABCDE']
  objlist = readobjlist(open('Ultima6/SAVEGAME/OBJLIST', 'rb'))
  for key,value in objlist.iteritems():
    objblk.setdefault(key,[])[:0] = value
    


def usage():
  print __doc__
  sys.exit()


def main():
  opts,args = getopt.getopt(sys.argv[1:], '')

  parse_everything()
  
  if not args: print "for usage use", sys.argv[0], "help"
  for a in args:
    if a == 'writejs':
      writejs()
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
  print "mkdir -p otiles"
  n = 0
  for y in range(64):
    for x in range(32):
      print 'convert -crop 16x16+%d+%d u6tiles+objects.png otiles/tile%03d.png' % \
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



def writejs():
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

  print "var objects = {";
  for k in objblk.keys():
    print k, ':', objblk[k], ','
  print "  };"

if __name__ == "__main__":
  main()
