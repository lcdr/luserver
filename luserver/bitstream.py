from pyraknet.bitstream import BitStream, c_bit, c_bool, c_double, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from .messages import Message

def write_header(self, subheader):
	self.write(c_ubyte(Message.LUPacket))
	self.write(c_ushort(type(subheader).header()))
	self.write(c_uint(subheader))
	self.write(c_ubyte(0x00))

BitStream.write_header = write_header
