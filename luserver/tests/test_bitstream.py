import unittest

from bitstream import c_ubyte, c_uint, c_ushort, ReadStream
from pyraknet.messages import Message
from luserver.bitstream import WriteStream
from luserver.messages import MessageType, WorldClientMsg


class WriteStreamTest(unittest.TestCase):
	def setUp(self):
		self.stream = WriteStream()

	def test_write_header(self):
		self.stream.write_header(WorldClientMsg.CharacterData)
		stream = ReadStream(bytes(self.stream))
		self.assertEqual(stream.read(c_ubyte), Message.UserPacket)
		self.assertEqual(stream.read(c_ushort), MessageType.WorldClient.value)
		self.assertEqual(stream.read(c_uint), WorldClientMsg.CharacterData.value)
		self.assertEqual(stream.read(c_ubyte), 0)
		self.assertTrue(stream.all_read())
