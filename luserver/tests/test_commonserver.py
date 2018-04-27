from unittest.mock import Mock

from pyraknet.bitstream import c_uint
from luserver.world import WorldServer
from luserver.auth import AuthServer
from luserver.bitstream import WriteStream
from luserver.messages import GeneralMsg
from luserver.tests.test_server import ServerTest

class CommonServerTest(ServerTest):
	ADDRESS = ("127.0.0.1", 23456)

	def set_up_server(self):
		return AuthServer("localhost", 10, Mock())

	def test_handshake(self):
		request = WriteStream()
		request.write_header(GeneralMsg.Handshake)
		request.write(c_uint(self.server._NETWORK_VERSION))
		request.write(bytes(4))
		request.write(c_uint(self.server._EXPECTED_PEER_TYPE))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)

		response = WriteStream()
		response.write_header(GeneralMsg.Handshake)
		response.write(c_uint(self.server._NETWORK_VERSION))
		response.write(bytes(4))
		response.write(c_uint(self.server._PEER_TYPE))
		self.assert_sent(response)

	def test_unexpected_network_version(self):
		request = WriteStream()
		request.write_header(GeneralMsg.Handshake)
		request.write(c_uint(1234))
		request.write(bytes(4))
		request.write(c_uint(self.server._EXPECTED_PEER_TYPE))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		self.server._server.close_connection.assert_called_once_with(self.ADDRESS)

	def test_unexpected_peer_type(self):
		request = WriteStream()
		request.write_header(GeneralMsg.Handshake)
		request.write(c_uint(self.server._NETWORK_VERSION))
		request.write(bytes(4))
		request.write(c_uint(1234))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		self.server._server.close_connection.assert_called_once_with(self.ADDRESS)
