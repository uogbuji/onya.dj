# onya.dj.serial.serato
# Read/write Serato crates
# Much wisdom gleaned from https://github.com/adammillerio/cratedigger
#      & https://github.com/jesseward/Serato-lib/blob/master/SSL-Crate.txt

# Note: binascii.unhexlify() & binascii.hexlify()

from os.path import basename, splitext, join
import re

SERATO_SCRATCHLIVE_BOILERPLATE = '/Serato ScratchLive Crate'.encode('utf-16-be')


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

    SERATO_DELIMITER = '%%'

    # Can be used as a warning of possible incompatability in crate files, based on the Serato value

    RECOGNIZED_SERATO_VERSIONS = ['81.0']

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
        return self.name.replace(crate.SERATO_DELIMITER, '/')

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
        s.consume(SERATO_SCRATCHLIVE_BOILERPLATE, strict=True)
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

    
# import io
# fp = io.BytesIO(b'abcdefghijklmnopqrstuvwxyz')
# s = parseable_bytestream(fp)
# s._read_bufsiz = 5
# pat = re.compile(rb'abc')
# t = s.consume(pat)

class parseable_bytestream:
    '''
    Wrapper that provides some parsing primitives for a byte stream

    self._fp - file-like object being parsed
    self._buffer = buffer with window of data retrieved from self._fp
    self._read_bufsiz - default amount to read from self._fp into self._buffer at a time
    self._index = position of parse relative to full self._fp contents
    self._prev = data just before the beginning of self._buffer, kept for debugging
    self._context_sizing - approx amount of data to display on either side of
        self._buffer[0] for debug purposes
    '''
    def __init__(self, fp):
        self._fp = fp
        self._buffer = b''
        self._read_bufsiz = 1024
        self._context_sizing = 16
        self._index = 0
        self._prev = b''
        self._fully_read = False

    def consume(self, pat, maxlength=0, strict=False):
        '''
        Consume the pattern (bytes regex or plain bytes for ) pat at the point
        of the stream make sure the bytes buffer being checked is at least as
        long as maxlength. pat can be a simple bytestring, for convenience.

        If the pattern is matched at the point, return the matching bytes
        and move the point immediately past them, otherwise leave the point
        unchanged

        If strict is true and the pattern can't be matched at the point, raise ValueError,
        otherwise leave the point unchanged

        Setting a short maxlength is basically an optimization, reducing the
        frequency of unnecessary string append operations

        >>> import re, io
        >>> fp = io.BytesIO(b'abcdefghijklmnopqrstuvwxyz')
        >>> s = parseable_bytestream(fp)
        >>> s._read_bufsiz = 5
        >>> pat = re.compile(rb'abc')
        >>> t = s.consume(pat)
        >>> t
        ... b'abc' # at this point s._buffer is b'de'
        >>> pat = re.compile(rb'def')
        >>> t = s.consume(pat, strict=True)
        ... b'def' # at this point s._buffer is b'ghij'
        
        '''
        maxlength = maxlength or self._read_bufsiz
        if len(self._buffer) < maxlength:
            reading = self._fp.read(max((maxlength, self._read_bufsiz)))
            self._buffer += reading
            if not reading: self._fully_read = True

        # matched, lm = None, 0
        if isinstance(pat, re.Pattern):
            m = pat.match(self._buffer)
            if m:
                matched = m.group(0)
                lm = len(matched)
                m = True
        else:
            m = self._buffer[:len(pat)] == pat
            lm = len(pat)
            matched = pat

        if m:
            self._prev += self._buffer[:lm]
            self._prev = self._prev[-self._context_sizing:]
            self._buffer = self._buffer[lm:]
            self._index += lm
            return matched
        elif strict:
            raise ValueError(f'Required data {pat} not found at position {self._index}')
        else:
            return b''

    def consume_len(self, nbytes, strict=False):
        '''
        Return bytes number of bytes at the point of the stream,
        and move the point immediately past them

        If strict is true and there are not enough bytes left in the stream,
        raise ValueError and leave the point unchanged
        '''
        if len(self._buffer) < nbytes:
            reading = self._fp.read(max((nbytes, self._read_bufsiz)))
            self._buffer += reading
            if not reading: self._fully_read = True
        if len(self._buffer) < nbytes and strict:
            raise ValueError(
                f'{nbytes} bytes required but only {len(self._buffer)} remain. Context: {self.context}'
                )
        else:
            self._index += nbytes
            self._prev += self._buffer[:nbytes]
            self._prev = self._prev[-self._context_sizing:]
            retval, self._buffer = self._buffer[:nbytes], self._buffer[nbytes:]
            return retval

    def lookahead(self, nbytes, strict=False):
        '''
        Return bytes number of bytes at the point of the stream,
        but do not move the point

        If strict is true and there are not enough bytes left in the stream,
        raise ValueError and leave the point unchanged
        '''
        if len(self._buffer) < nbytes:
            reading = self._fp.read(max((nbytes, self._read_bufsiz)))
            self._buffer += reading
            if not reading: self._fully_read = True
        if len(self._buffer) < nbytes and strict:
            raise ValueError(
                f'{nbytes} bytes required but only {len(self._buffer)} remain. Context: {self.context}'
                )
        else:
            return self._buffer[:nbytes]

    def consume_until(self, pat, maxlength=0, strict=False):
        '''
        Consume the pattern (bytes regex) pat at the point of the stream
        Make sure the bytes buffer being checked is at least as long as
        maxlength

        If the pattern is matched at the point, return the matching bytes
        and move the point immediately past them, otherwise leave the point
        unchanged

        If strict is true and the pattern can't be matched at the point, raise ValueError,
        otherwise leave the point unchanged        
        '''
        pass


    def COPIEDASIS_write_int(self, write_int: int, length: int = 4) -> None:
        """Write an arbitrary int
        Args:
        write_int (int): Integer to write
        length (int): Number of bytes to use for representing the int
        """

        # Convert the int provided to bytes of provided length and write it
        self._stream.write(write_int.to_bytes(length, byteorder='big'))


    @property
    def context(self):
        '''
        Return a string representation of the current context, for debugging,
        based on self._context_sizing bytes either side of self._buffer[0]
        '''
        # FIXME: Guard against cases where self._buffer isn't at least
        # self._context_sizing long, but could be
        return ''.join((self._prev.hex(' '), ' ^ ', self._buffer[:self._context_sizing].hex(' ')))

    @property
    def exhausted(self):
        '''
        Return a True if there is no more to process in the buffer or the file epointer
        '''
        return self._fully_read and not self._buffer


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
