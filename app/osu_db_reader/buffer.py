# from https://github.com/jaasonw/osu-db-tools/blob/master/buffer.py

import struct


class ReadBuffer:

    @staticmethod
    def read_bool(buffer) -> bool:
        return struct.unpack('<?', buffer.read(1))[0]


    @staticmethod
    def read_ubyte(buffer) -> int:
        return struct.unpack('<B', buffer.read(1))[0]


    @staticmethod
    def read_ushort(buffer) -> int:
        return struct.unpack('<H', buffer.read(2))[0]


    @staticmethod
    def read_uint(buffer) -> int:
        return struct.unpack('<I', buffer.read(4))[0]


    @staticmethod
    def read_float(buffer) -> float:
        return struct.unpack('<f', buffer.read(4))[0]


    @staticmethod
    def read_double(buffer) -> float:
        return struct.unpack('<d', buffer.read(8))[0]


    @staticmethod
    def read_ulong(buffer) -> int:
        return struct.unpack('<Q', buffer.read(8))[0]


    # osu specific
    @staticmethod
    def read_int_double(buffer):
        ReadBuffer.read_ubyte(buffer)
        integer = ReadBuffer.read_uint(buffer)
        ReadBuffer.read_ubyte(buffer)
        double = ReadBuffer.read_double(buffer)
        return (integer, double)


    @staticmethod
    def read_timing_point(buffer):
        bpm = ReadBuffer.read_double(buffer)
        offset = ReadBuffer.read_double(buffer)
        inherited = ReadBuffer.read_bool(buffer)
        return (bpm, offset, inherited)


    @staticmethod
    def read_string(buffer) -> str:
        strlen, strflag = 0, ReadBuffer.read_ubyte(buffer)
        if strflag == 0x0b:
            strlen, shift = 0, 0

            # uleb128
            # https://en.wikipedia.org/wiki/LEB128
            while True:
                byte = ReadBuffer.read_ubyte(buffer)
                strlen |= ((byte & 0x7F) << shift)

                if (byte & (1 << 7)) == 0:
                    break

                shift += 7

        return (struct.unpack(f'<{strlen}s', buffer.read(strlen))[0]).decode('utf-8')



class WriteBuffer:

    def __init__(self):
        self.offset = 0
        self.data = b''


    def write_bool(self, data: bool):
        self.data += struct.pack('<?', data)


    def write_ubyte(self, data: int):
        self.data += struct.pack('<B', data)


    def write_ushort(self, data: int):
        self.data += struct.pack('<H', data)


    def write_uint(self, data: int):
        self.data += struct.pack('<I', data)


    def write_float(self, data: float):
        self.data += struct.pack('<f', data)


    def write_double(self, data: float):
        self.data += struct.pack('<d', data)


    def write_ulong(self, data: int):
        self.data += struct.pack('<Q', data)


    def write_string(self, data: str):
        if len(data) <= 0: 
            self.write_ubyte(0x0)
            return

        self.write_ubyte(0x0b)
        strlen = b''
        value = len(data)

        while value != 0:
            byte = (value & 0x7F)
            value >>= 7

            if (value != 0):
                byte |= 0x80

            strlen += struct.pack('<B', byte)

        self.data += strlen
        self.data += struct.pack(f'<{len(data)}s', data.encode('utf-8'))


    def clear_buffer(self):
        self.data = b''