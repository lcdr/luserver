import unittest
from unittest.mock import Mock

class ServerTest(unittest.TestCase):
	USERNAME = "name"
	PASSWORD = "password"
	ADDRESS = ("127.0.0.1", 12345)

	def setUp(self):
		self.set_up_db()
		self.server = self.set_up_server()
		self.server._server.send = Mock()
		self.server._server.close_connection = Mock()

	def set_up_db(self):
		self.conn = Mock()
		self.db = self.conn.root
		self.db.accounts = {}

	def set_up_server(self):
		raise NotImplementedError

	def assert_sent(self, stream):
		self.server._server.send.assert_called_once_with(bytes(stream), self.ADDRESS, False)

	def assert_broadcast(self, stream):
		self.server._server.send.assert_called_once_with(bytes(stream), None, True)
