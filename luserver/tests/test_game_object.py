from enum import Enum
from unittest.mock import Mock, patch

from bitstream import c_bit, c_float, c_int, c_int64, c_uint, c_ushort, ReadStream
from luserver.tests.test_world import SessionWorldTest
from luserver.bitstream import WriteStream
from luserver.messages import WorldClientMsg
from luserver.game_object import broadcast, c_int_, EBY, EF, EI, EO, ES, GameObject

class GameObjectTest(SessionWorldTest):
	def sample_game_message(self, p_int:c_int_=EI, p_bool:bool=True, p_default:c_int_=42, p_default2:c_int_=42, p_float:float=EF,p_bytes:bytes=EBY, p_str:str=ES, p_obj: GameObject=EO) -> None:
		self.mock(p_int, p_bool, p_default, p_default2, p_float, p_bytes, p_str, p_obj)

	gm_broadcast = broadcast(sample_game_message)

	def sample_game_message_player(self, player, p_int:c_int_=EI) -> None:
		self.mock(player, p_int)

	def test_on_game_message(self):
		self.mock = Mock()
		stream = WriteStream()
		stream.write(c_ushort(12345))
		stream.write(c_int(12345))
		stream.write(c_bit(True))
		stream.write(c_bit(False))
		stream.write(c_bit(True))
		stream.write(c_int(21))
		stream.write(c_float(8.125))
		stream.write(b"hello", length_type=c_uint)
		stream.write("world", length_type=c_uint)
		stream.write(c_int64(self.player.object_id))
		data = bytes(stream)

		with patch("luserver.game_object.GameMessage", Enum("GameMessage", {"SampleGameMessage": 12345})):
			with patch("luserver.game_object.GameObject.handlers", return_value=[self.sample_game_message]):
				self.player.on_game_message(ReadStream(data), self.ADDRESS)
				self.mock.assert_called_once_with(12345, True, 42, 21, 8.125, b"hello", "world", self.player)
			self.mock = Mock()

	def test_player_on_game_message(self):
		self.mock = Mock()
		stream = WriteStream()
		stream.write(c_ushort(12345))
		stream.write(c_int(12345))
		data = bytes(stream)

		with patch("luserver.game_object.GameMessage", Enum("GameMessage", {"SampleGameMessage": 12345})):
			with patch("luserver.game_object.GameObject.handlers", return_value=[self.sample_game_message_player]):
				self.player.on_game_message(ReadStream(data), self.ADDRESS)
			self.mock.assert_called_once_with(self.player, 12345)

	def test_send_game_message(self):
		self.mock = Mock()
		self.object = self.player

		with patch("luserver.game_object.GameMessage", Enum("GameMessage", {"SampleGameMessage": 12345})):
			self.gm_broadcast(12345, p_float=4.20, p_bytes=b"test", p_str="test", p_obj=self.player)
		self.mock.assert_called_once_with(12345, True, 42, 42, 4.2, b"test", "test", self.player)
		stream = WriteStream()
		stream.write_header(WorldClientMsg.GameMessage)
		stream.write(c_int64(self.player.object_id))
		stream.write(c_ushort(12345))
		stream.write(c_int(12345))
		stream.write(c_bit(True))
		stream.write(c_bit(False))
		stream.write(c_bit(False))
		stream.write(c_float(4.20))
		stream.write(b"test", length_type=c_uint)
		stream.write("test", length_type=c_uint)
		stream.write(c_int64(self.player.object_id))
		self.assert_broadcast(stream)
