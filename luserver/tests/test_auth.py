import asyncio
import datetime
from unittest.mock import patch

from pyraknet.bitstream import c_ubyte, c_uint, c_ushort
from luserver.world import WorldServer
from luserver.auth import Account, AuthServer, _LoginMessage, _LoginReturnCode, PasswordState
from luserver.bitstream import WriteStream
from luserver.messages import AuthServerMsg, WorldClientMsg
from luserver.tests.test_server import ServerTest

class AuthTest(ServerTest):
	SERVER_HOST = "127.0.0.1"
	SERVER_PORT = 4321

	def set_up_db(self):
		super().set_up_db()
		self.db.config = {"auth_enabled": True}

	def set_up_server(self):
		with patch("pyraknet.server.Server._init_network", self.init_network):
			server = AuthServer("localhost", 10, self.conn)
		server._on_login_request = self.on_login_request
		self.db.servers = {(self.SERVER_HOST, self.SERVER_PORT): (0, 0, 0)}
		return server

	async def init_network(self) -> None:
		pass

	async def on_login_request(self, request, address):
		try:
			await AuthServer._on_login_request(self.server, request, address)
		finally:
			asyncio.get_event_loop().stop()

	def send_login_request(self, username=ServerTest.USERNAME, password=ServerTest.PASSWORD):
		request = WriteStream()
		request.write_header(AuthServerMsg.LoginRequest)
		request.write(username, allocated_length=33)
		request.write(password, allocated_length=41)
		request.write(bytes(803))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		asyncio.get_event_loop().run_forever()

	def write_invalid_u_or_pw_resp(self):
		response = WriteStream()
		response.write_header(WorldClientMsg.LoginResponse)
		response.write(c_ubyte(_LoginReturnCode.InvalidUsernameOrPassword))
		response.write(bytes(264))
		response.write(c_ushort(1))
		response.write(c_ushort(10))
		response.write(c_ushort(64))
		response.write(bytes(225))
		response.write(c_uint(4))
		return response

	def write_login_message(self, message):
		response = WriteStream()
		response.write_header(WorldClientMsg.LoginResponse)
		response.write(c_ubyte(_LoginReturnCode.InsufficientAccountPermissions))
		response.write(bytes(264))
		response.write(c_ushort(1))
		response.write(c_ushort(10))
		response.write(c_ushort(64))
		response.write(bytes(223))
		response.write(message, length_type=c_ushort)
		response.write(c_uint(4))
		return response

class AuthDisabledTest(AuthTest):
	AUTH_DISABLED_MSG = "auth disabled"

	def set_up_db(self):
		super().set_up_db()
		self.db.config["auth_enabled"] = False
		self.db.config["auth_disabled_message"] = self.AUTH_DISABLED_MSG

	def test_auth_disabled(self):
		self.send_login_request()
		self.assert_sent(self.write_login_message(self.AUTH_DISABLED_MSG))

class NoAccountAuthTest(AuthTest):
	def test_no_account(self):
		self.send_login_request()
		self.assert_sent(self.write_invalid_u_or_pw_resp())

class ExistingAccountAuthTest(AuthTest):
	def set_up_db(self):
		super().set_up_db()
		self.db.accounts[self.USERNAME] = Account(self.USERNAME, self.PASSWORD)

	def test_incorrect_password(self):
		self.send_login_request(password="incorrect")
		self.assert_sent(self.write_invalid_u_or_pw_resp())

	def test_correct_password(self):
		with patch("secrets.token_hex", return_value="0"):
			self.send_login_request()

		response = WriteStream()
		response.write_header(WorldClientMsg.LoginResponse)
		response.write(c_ubyte(_LoginReturnCode.Success))
		response.write(bytes(264))
		response.write(c_ushort(1))
		response.write(c_ushort(10))
		response.write(c_ushort(64))
		response.write("0", allocated_length=33)
		response.write(self.SERVER_HOST.encode("latin-1"), allocated_length=33)
		response.write(bytes(33))
		response.write(c_ushort(self.SERVER_PORT))
		response.write(bytes(91))
		response.write(c_uint(4))
		self.assert_sent(response)

	def test_account_banned(self):
		BAN_TIMESTAMP = 2**32
		self.db.accounts[self.USERNAME].banned_until = BAN_TIMESTAMP
		self.send_login_request()
		self.assert_sent(self.write_login_message(_LoginMessage.AccountBanned % datetime.datetime.fromtimestamp(BAN_TIMESTAMP)))

	def test_account_temp_password(self):
		self.db.accounts[self.USERNAME].set_password("temp")
		self.db.accounts[self.USERNAME].password_state = PasswordState.Temp
		self.send_login_request(password="temp")
		self.assert_sent(self.write_login_message(_LoginMessage.PasswordIsTemp))
		self.server._server.send.reset_mock()
		self.send_login_request(password="temp")
		self.assert_sent(self.write_login_message(_LoginMessage.SameTempPassword))
		self.server._server.send.reset_mock()
		self.send_login_request()
		self.assert_sent(self.write_login_message(_LoginMessage.PasswordSet))
		self.server._server.send.reset_mock()
		self.test_correct_password()
