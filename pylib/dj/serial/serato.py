# onya.dj.serial.serato
# Read/write Serato crates
# Includes some wisdom gleaned from https://github.com/adammillerio/cratedigger
#      & https://github.com/crobinso/scratchlivedb/blob/master/scratchlivedb/scratchdb.py
#      & https://github.com/jesseward/Serato-lib/blob/master/SSL-Crate.txt

# Note: binascii.unhexlify() & binascii.hexlify()

import re
import sys
from os.path import basename, splitext, join

from onya.etc.bytesutil import parseable_bytestream, parseable_bytebuffer

SERATO_CRATE_INDIC = '/Serato ScratchLive Crate'.encode('utf-16-be')
SERATO_DB_INDIC = '/Serato Scratch LIVE Database'.encode('utf-16-be')

# Can be used as a warning of possible incompatability in crate files, based on the Serato value
RECOGNIZED_SERATO_VERSIONS = ['81.0', '@2.0']


class crate:
    '''
    Serato crates are binary files on disk, in an undocumented format

    Note: The cratedigger project identifies the following crate attributes:
    sort - e.g. crates can be sorted by song name, BPM, etc. Feels like this should be more about runtime & less about crate metadata, though!
    sort_rev - Unknown what this does or means, but hard-coded to 256?
    columns - Headers in the crate: ['song', 'artist', 'album', 'length']

    Crates also have a name, a list of tracks, optional parent and children

    >>> from pathlib import Path
    >>> c = crate()
    >>> c.load(str(Path.home() / Path('Music/_Serato_/Subcrates/Incoming%%Sounds.crate')))
    '''
    # Serato crate nesting is represented with path from root using the '%%' delimiter
    # Note: "crate" & "subcrate" terminology is used fairly interchangeably in Serato

    HIERARCHY_DELIMITER = '%%'

    def __init__(self):
        self.version = self.sort = self.sort_rev = self.name = self.children = None
        self.tracks = []
        self.columns = ['song', 'artist', 'album', 'length']

    def read(fp):
        '''
        fp - file-like object
        '''
        pass

    def __str__(self):
        '''
        Returns the Crate name, with delimiter replaced by forward slash
        '''
        return self.name.replace(crate.HIERARCHY_DELIMITER, '/')

    def load(self, path):
        '''
        Load from Serato .crate file

        Args:
            path (str): Path to the .crate file

        Raises:
            ValueError: Catch-all for parsing problems while loading the crate
        '''
        # Set crate path
        self.name = splitext(basename(path))[0]

        # Open crate file as binary BufferedReader
        fp = open(path, 'rb')

        # Header
        # Load the version
        s = parseable_bytestream(fp)
        s.consume(b'vrsn\x00\x00', strict=True)
        self.version = s.consume_len(8).decode('utf-16-be')     # Set version from next 8 bytes as UTF-16 string
        # print(s.context)
        s.consume(SERATO_CRATE_INDIC, strict=True)
        print(s.context)

        # Parse header sections until we reach the tracks (otrk) section
        # Get the first section
        while not s.exhausted:
            try:
                # Read the next section
                section = s.consume_len(4)
                print('section:', repr(section))
            except ValueError:
                # If the read didn't get 4 bytes, then we must be at the end of a crate
                # with no tracks, so just end the load here
                fp.close()
                return
        
            if section == b'otrk':
                # If the section is otrk, it's time to start reading tracks
                break
            elif section == b'ovct':
                # Parse columns details (ovct)
                # This pattern occurs once for every column
                # Example:
                # ovct\x00\x00\x00\x1atvcn\x00\x00\x00\x08\x00s\x00o\x00n\x00gtvcw\x00\x00\x00\x02\x000
                # ovct = 26 (0000001A)
                # tvcn = 8 (00000008)
                # column = 'song'
                # tvcw = 2 (0002)
                print(s.context)
                ovct = int.from_bytes(s.consume_len(4), byteorder='big')
                s.consume(b'tvcn', strict=True)
                tvcn = int.from_bytes(s.consume_len(4), byteorder='big')
                # Column name as UTF-16 string of tvcn length
                colname = s.consume_len(tvcn).decode('utf-16-be')
                print('Column:', colname)
                self.columns.append(colname)
                s.consume(b'tvcw', strict=True)
                tvcw = int.from_bytes(s.consume_len(4), byteorder='big')
                # print('ovct info:', ovct, tvcn, tvcw)

                # Bogus assertions, apparently
                # difference = ovct - tvcn
                # if difference != 18:
                #     raise ValueError(f'Expected (ovct - tvcn) to be 18, but found {difference} (osrt = {ovct}, tvcn = {tvcn})')
                
                # Fail if tvcw is not 2
                # if tvcw != 2:
                #     raise ValueError(f'Expected tvcw to be 2, but found {tvcw}')
            elif section == b'osrt':
                # Parse column sorting (osrt)
                # This pattern occurs only once
                # Example:
                # osrt\x00\x00\x00\x19tvcn\x00\x00\x00\x08\x00s\x00o\x00n\x00gbrev\x00\x00\x00\x01\x00
                # osrt = 25 (00000019)
                # tvcn = 8 (00000008)
                # sort = 'song'
                # sort_rev = 256
                osrt = int.from_bytes(s.consume_len(4), byteorder='big')
                s.consume(b'tvcn', strict=True)
                tvcn = int.from_bytes(s.consume_len(4), byteorder='big')
                # Column name as UTF-16 string of tvcn length
                colname = s.consume_len(tvcn).decode('utf-16-be')
                print('Column:', colname)
                self.columns.append(colname)
                s.consume(b'brev', strict=True)
                self.sort_rev = int.from_bytes(s.consume_len(5), byteorder='big')
                print('osrt info:', osrt, tvcn, self.sort_rev)

                difference = osrt - tvcn
                if difference != 17:
                    raise ValueError(f'Expected (osrt - tvcn) to be 17, but found {difference} (osrt = {osrt}, tvcn = {tvcn})')
            else:
                # Section starts with 'os', 'ot' or 'ov', but is yet not a known section
                # print(s.context, file=sys.stderr)
                raise ValueError(f'Encountered unknown header section {section}')

            # Consume a variable number of 2-byte sequences such as "\000" or
            # even "\002\005\000". No info available on what these are for
            # We can stop when we see what looks like the start of a new section
            # We also stop if we get to the end of the stream (in which case it's an empty crate)
            while s.lookahead(2) not in (b'os', b'ot', b'ov') and not s.exhausted:
                s.consume_len(2)
                
        
        # Parse tracks
        # Example:
        # otrk\x00\x00\x00\x8aptrk\x00\x00\x00\x82\x00M\x00u\x00s\x00i\x00c\x00/
        # \x00F\x00L\x00A\x00C\x00/\x008\x00m\x00m\x00/\x008\x00m\x00m\x00 \x00-
        # \x00 \x00O\x00p\x00e\x00n\x00e\x00r\x00 \x00E\x00P\x00/\x000\x001\x00 
        # \x00-\x00 \x008\x00m\x00m\x00 \x00-\x00 \x00O\x00p\x00e\x00n\x00e\x00r
        # \x00 \x00E\x00P\x00 \x00-\x00 \x00O\x00p\x00e\x00n\x00e\x00r\x00.\x00f
        # \x00l\x00a\x00c
        # otrk = 138 (0000008A)
        # ptrk = 130 (00000082)
        # track = 'Music/FLAC/8mm/8mm - Opener EP/01 - 8mm - Opener EP - Opener.flac'
        first_track = True
        # Condition handles empty crate case
        while not s.exhausted:
            if not first_track:
                # Skip otrk unless this is the first track
                # On the first track it was skipped during header parsing
                try:
                    s.consume(b'otrk', strict=True)
                except ValueError:
                    # If we got an exception, then this is the end of the file
                    break

            first_track = False

            otrk = int.from_bytes(s.consume_len(4), byteorder='big')
            s.consume(b'ptrk', strict=True)
            ptrk = int.from_bytes(s.consume_len(4), byteorder='big')

            difference = otrk - ptrk
            if difference != 8:
                raise ValueError(f'Expected (otrk - ptrk) to be 8, but found {difference} (otrk = {otrk}, ptrk = {ptrk})')
            
            # Read UTF-16 string of ptrk length to get track filepath & append it
            track_path = s.consume_len(ptrk).decode('utf-16-be')
            print('Track name:', track_path)
            self.tracks.append(track_path)

        fp.close()


'''
# Notice the \00\2\00\5\00\0at the end of 00000070
$ hexdump -C "/Users/uche/Music/_Serato_/Subcrates/Regular sets%%B-GrownUps.crate"
00000000  76 72 73 6e 00 00 00 38  00 31 00 2e 00 30 00 2f  |vrsn...8.1...0./|
00000010  00 53 00 65 00 72 00 61  00 74 00 6f 00 20 00 53  |.S.e.r.a.t.o. .S|
00000020  00 63 00 72 00 61 00 74  00 63 00 68 00 4c 00 69  |.c.r.a.t.c.h.L.i|
00000030  00 76 00 65 00 20 00 43  00 72 00 61 00 74 00 65  |.v.e. .C.r.a.t.e|
00000040  6f 73 72 74 00 00 00 17  74 76 63 6e 00 00 00 06  |osrt....tvcn....|
00000050  00 62 00 70 00 6d 62 72  65 76 00 00 00 01 00 6f  |.b.p.mbrev.....o|
00000060  76 63 74 00 00 00 1e 74  76 63 6e 00 00 00 08 00  |vct....tvcn.....|
00000070  73 00 6f 00 6e 00 67 74  76 63 77 00 00 00 06 00  |s.o.n.gtvcw.....|
00000080  32 00 35 00 30 6f 76 63  74 00 00 00 24 74 76 63  |2.5.0ovct...$tvc|
00000090  6e 00 00 00 12 00 70 00  6c 00 61 00 79 00 43 00  |n.....p.l.a.y.C.|
000000a0  6f 00 75 00 6e 00 74 74  76 63 77 00 00 00 02 00  |o.u.n.ttvcw.....|
000000b0  30 6f 76 63 74 00 00 00  1e 74 76 63 6e 00 00 00  |0ovct....tvcn...|
000000c0  0c 00 61 00 72 00 74 00  69 00 73 00 74 74 76 63  |..a.r.t.i.s.ttvc|
000000d0  77 00 00 00 02 00 30 6f  76 63 74 00 00 00 18 74  |w.....0ovct....t|
000000e0  76 63 6e 00 00 00 06 00  62 00 70 00 6d 74 76 63  |vcn.....b.p.mtvc|
000000f0  77 00 00 00 02 00 30 6f  76 63 74 00 00 00 18 74  |w.....0ovct....t|
00000100  76 63 6e 00 00 00 06 00  6b 00 65 00 79 74 76 63  |vcn.....k.e.ytvc|
00000110  77 00 00 00 02 00 30 6f  76 63 74 00 00 00 1c 74  |w.....0ovct....t|
00000120  76 63 6e 00 00 00 0a 00  61 00 6c 00 62 00 75 00  |vcn.....a.l.b.u.|
00000130  6d 74 76 63 77 00 00 00  02 00 30 6f 76 63 74 00  |mtvcw.....0ovct.|
00000140  00 00 1e 74 76 63 6e 00  00 00 0c 00 6c 00 65 00  |...tvcn.....l.e.|
00000150  6e 00 67 00 74 00 68 74  76 63 77 00 00 00 02 00  |n.g.t.htvcw.....|
00000160  30 6f 76 63 74 00 00 00  20 74 76 63 6e 00 00 00  |0ovct... tvcn...|
00000170  0e 00 63 00 6f 00 6d 00  6d 00 65 00 6e 00 74 74  |..c.o.m.m.e.n.tt|
00000180  76 63 77 00 00 00 02 00  30                       |vcw.....0|
'''

import functools



# Dispatch tables of known top-level sections
TOP_SECTION = {}

# Dispatch tables of known DB sections
OTRK_FIELD = {}

def handle_section(bs):
    '''
    Determine the current section, and return a handler function, if known

    bs - bytes source (bytestream or bytebuffer) ready for read
    '''
    try:
        # Read the next section
        key = bs.consume_len(4)
        print('section:', repr(key))
    except ValueError:
        # If the read didn't get 4 bytes, then we must be at the end of file
        return None

    try:
        # Read data length
        datalen = int.from_bytes(bs.consume_len(4), byteorder='big')
        # Column name as UTF-16 string of tvcn length
        data = s.consume_len(datalen)
    except ValueError:
        # If the read didn't get 4 bytes, then we must be at the end of file
        return None

    handler = KNOWN_SECTIONS.get(key)
    if handler:
        retval = handler(data)
        return retval

    return None


def lookup_field(s):
    try:
        # Read the next section
        key = s.consume_len(4)
        # Read data length
        datalen = int.from_bytes(s.consume_len(4), byteorder='big')
        # Column name as UTF-16 string of tvcn length
        data = s.consume_len(datalen)
        return key, data
    except ValueError:
        # If the read didn't get 4 bytes, then we must be at the end of file
        return None, None


# Handler decorator
def handler(code, context):
    def _handler(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        context[code] = wrapper
        return wrapper
    return _handler


@handler(b'otrk', TOP_SECTION)
def otrk(data):
    '''
    Handle otrk section
    '''
    pass

@handler(b'ttyp', OTRK_FIELD)
def ttyp(data):
    '''
    Track type (mp3, wav, flac, etc.)
    '''
    return data.decode('utf-16-be')

@handler(b'pfil', OTRK_FIELD)
def pfil(data):
    '''
    full path to audio file on disk
    '''
    return data.decode('utf-16-be')

@handler(b'tart', OTRK_FIELD)
def tart(data):
    'track artist'
    return data.decode('utf-16-be')

@handler(b'tsng', OTRK_FIELD)
def tsng(data):
    'track song title'
    return data.decode('utf-16-be')

@handler(b'talb', OTRK_FIELD)
def talb(data):
    'track album'
    return data.decode('utf-16-be')

@handler(b'tcom', OTRK_FIELD)
def tcom(data):
    'track composer'
    return data.decode('utf-16-be')

@handler(b'tlen', OTRK_FIELD)
def tlen(data):
    'track length'
    return data.decode('utf-16-be')

@handler(b'tbit', OTRK_FIELD)
def tbit(data):
    'track bit rate'
    return data.decode('utf-16-be')

@handler(b'tbpm', OTRK_FIELD)
def tbpm(data):
    'track BPM'
    return data.decode('utf-16-be')

@handler(b'tlen', OTRK_FIELD)
def tlen(data):
    'track length (time)'
    return data.decode('utf-16-be')

@handler(b'ttyr', OTRK_FIELD)
def ttyr(data):
    'track year'
    return data.decode('utf-16-be')

@handler(b'tsiz', OTRK_FIELD)
def tsiz(data):
    'track size'
    return data.decode('utf-16-be')

@handler(b'tsmp', OTRK_FIELD)
def tsmp(data):
    'track sample rate'
    return data.decode('utf-16-be')

@handler(b'tcor', OTRK_FIELD)
def tcor(data):
    'track corruption explanation (plain text)'
    return data.decode('utf-16-be')

# tadd :  track date added
# tcom :  track comment
# tgen :  track genre
# tgrp :  track grouping
# tkey :  track musical key
# tlbl :  track release label
# tlen :  track 
# trmx :  track remixer

class db:
    '''
    Serato DBs are binary files on disk, in an undocumented format, similar to crate format
    >>> from pathlib import Path
    >>> sdb = crate()
    >>> sdb.load(str(Path.home() / Path('Music/_Serato_/Subcrates/Incoming%%Sounds.crate')))
    '''
    # Serato crate nesting is represented with path from root using the '%%' delimiter
    # Note: "crate" & "subcrate" terminology is used fairly interchangeably in Serato

    HIERARCHY_DELIMITER = '%%'

    def __init__(self):
        self.version = self.sort = self.sort_rev = self.name = None
        self.tracks = []
        #self.columns = ['song', 'artist', 'album', 'length']
        self.columns = set()

    def __str__(self):
        '''
        The DB name
        '''
        return 'Serato Scratch LIVE Database'

    def load(self, path):
        '''
        Load from Serato DB file

        Args:
            path (str): Path to the DB file

        Raises:
            ValueError: Catch-all for parsing problems while loading the crate
        '''
        # Open DB file as binary BufferedReader
        fp = open(path, 'rb')

        # Header
        # Load the version
        s = parseable_bytestream(fp)
        s.consume(b'vrsn\x00\x00', strict=True)
        self.version = s.consume_len(8).decode('utf-16-be')     # Set version from next 8 bytes as UTF-16 string
        # print(s.context)
        s.consume(SERATO_DB_INDIC, strict=True)
        # Seems to be only otrk sections
        while not s.exhausted:
            # print(s.context, file=sys.stderr)
            key, raw_data = lookup_field(s)
            # Assume empty section indicates end of DB
            if key == b'':
                break
            if key != b'otrk':
                print(f'Unknown section: "{key}"', file=sys.stderr)
            t = self.load_track(parseable_bytebuffer(raw_data))
            self.tracks.append(track(t))

        fp.close()

    def load_track(self, data):
        t = {}
        while not data.exhausted:
            key, raw_val = lookup_field(data)
            if key in OTRK_FIELD:
                func = OTRK_FIELD[key]
                val = func(raw_val)
                print(f'"{key}", value "{val}"', file=sys.stderr)
                t[key.decode('utf-8')] = val
            else:
                if key == b'':
                    break
                print(f'UNKNOWN field: "{key}", value "{raw_val}"', file=sys.stderr)
        if 'tbpm' in t:
            t['tbpm'] = round(float(t['tbpm']))
        # t['tbpm'] = f'{float(t.get("tbpm", "0")):.0f}'
        # t['tbpm'] = '?' if t['tbpm'] == '0' else t['tbpm']
        # t['enc'] = f'{{{t.get("tbpm", "?").partition(".")[0]}, {t.get("ttyp", "?")}}}'
        # print(f'TRACKINFO: "{t}"', file=sys.stderr)
        return t

    @property
    def track_data_frame(self):
        try:
            return self._tdf
        except AttributeError:
            self.dataframe_prep()
            return self._tdf

    def dataframe_prep(self):
        '''
        Return a Pandas dataframe with track data
        '''
        import pandas as pd
        import numpy as np

        self._tdf = pd.DataFrame(self.tracks)

        delim = '|'
        # Index for searching
        self._stdf = {
            i: f'{t.get("tart", "")}{delim}{t.get("tsng", "")}{delim}{t.get("talb", "")}{delim}{t.get("tcom", "")}'
            for (i, t) in self._tdf.iterrows()
        }
        return

    def search(self, q):
        '''
        Search the track DB for a simple query string. Return a results data frame

        Some useful notes on fozzywuzzy over Pandas: http://jonathansoma.com/lede/algorithms-2017/classes/fuzziness-matplotlib/fuzzing-matching-in-pandas-with-fuzzywuzzy/
        '''
        from fuzzywuzzy import fuzz, process
        # Make sure we're set up
        self.track_data_frame
        # return process.extractBests(q, self._stdf, scorer=fuzz.partial_ratio, score_cutoff=90, limit=100)
        res = process.extractBests(q, self._stdf, scorer=fuzz.partial_ratio, score_cutoff=90)
        res_ix = [ r[2] for r in res ]
        #return res_ix
        # return self._tdf[self._tdf['xxx'].isin(res_ix)]
        return self._tdf.iloc[res_ix][['tart', 'tsng', 'talb', 'tbpm']]


class track(dict):
    def __str__(self):
        return f'{self.get("tart", "")} - {self.get("tsng", "")} - {self.get("talb", "")} \
{{{self.get("tbpm", "?").partition(".")[0]}, {self.get("ttyp", "?")}}}'

