from bitstream import c_ubyte, c_uint, c_ushort
from bitstream import WriteStream as _WriteStream
from pyraknet.messages import Message
from .messages import ENUM_TO_MSG, LUMessage

class WriteStream(_WriteStream):
	def write_header(self, subheader: LUMessage) -> None:
		self.write(c_ubyte(Message.UserPacket.value))
		self.write(c_ushort(ENUM_TO_MSG[type(subheader)]))
		self.write(c_uint(subheader.value))
		self.write(c_ubyte(0x00))
