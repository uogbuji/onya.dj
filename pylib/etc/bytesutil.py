# pylib.etc.bytesutil

import re


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


