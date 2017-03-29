from pyraknet.bitstream import c_bit, c_bool, c_double, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, ReadStream, WriteStream
from pyraknet.messages import Message

class WriteStream(WriteStream):
	def write_header(self, subheader):
		self.write(c_ubyte(Message.UserPacket))
		self.write(c_ushort(subheader.header()))
		self.write(c_uint(subheader))
		self.write(c_ubyte(0x00))
