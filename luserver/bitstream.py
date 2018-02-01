from pyraknet.bitstream import c_ubyte, c_uint, c_ushort
from pyraknet.bitstream import WriteStream as _WriteStream
from pyraknet.messages import Message
from .messages import LUMessage

class WriteStream(_WriteStream):
	def write_header(self, subheader: LUMessage) -> None:
		self.write(c_ubyte(Message.UserPacket))
		self.write(c_ushort(subheader.header()))
		self.write(c_uint(subheader))
		self.write(c_ubyte(0x00))
