import logging
import random

try:
	import bcrypt
	from passlib.hash import bcrypt as encryption
except ImportError:
	from passlib.hash import pbkdf2_sha256 as encryption
from persistent import Persistent
from persistent.mapping import PersistentMapping

from . import server
from .bitstream import BitStream, c_bool, c_ubyte, c_uint, c_ushort
from .messages import AuthServerMsg, GeneralMsg, WorldClientMsg

log = logging.getLogger(__name__)

class LoginReturnCode:
	GeneralFailure = 0
	Success = 1
	AccountBanned = 2
	InsufficientAccountPermissions = 5
	InvalidUsernameOrPassword = 6
	AccountLocked = 7 # when wrong password is entered too many times
	# 8 is the same as 6, possible distinction between username/password?
	AccountActivationPending = 9
	AccountDisabled = 10
	GameTimeExpired = 11
	FreeTrialEnded = 12
	PlaySchedule = 13
	AccountNotActivated = 14

class AuthServer(server.Server):
	PEER_TYPE = AuthServerMsg.header()

	def __init__(self, host, max_connections, db_conn):
		super().__init__((host, 1001), max_connections, db_conn)
		self.db.servers.clear()
		self.conn.transaction_manager.commit()

	def on_handshake(self, data, address):
		super().on_handshake(data, address)
		self.register_handler(AuthServerMsg.LoginRequest, self.on_login_request, address)

	async def on_login_request(self, request, address):
		self.conn.sync()
		username = request.read(str, allocated_length=66)
		password = request.read(str, allocated_length=82)

		return_code = LoginReturnCode.Success
		if username.lower() not in self.db.accounts:
			# Account not in database, create!
			self.db.accounts[username.lower()] = Account(username, encryption.encrypt(password), address)
			self.conn.transaction_manager.commit()
		else:
			if not encryption.verify(password, self.db.accounts[username.lower()].password):
				return_code = LoginReturnCode.InvalidUsernameOrPassword

		account = self.db.accounts[username.lower()]

		response = BitStream()
		response.write_header(WorldClientMsg.LoginResponse)
		response.write(c_ubyte(return_code))
		response.write(bytes(264))
		# client version
		response.write(c_ushort(1))
		response.write(c_ushort(10))
		response.write(c_ushort(64))

		redirect_host, redirect_port = "", 0
		if return_code == LoginReturnCode.Success:
			if account.address is not None and account.address != address:
				log.info("Disconnecting duplicate at %s", account.address)
				#self.close_connection(account.address, server.DisconnectReason.DuplicateLogin)

				#duplicate_notify = BitStream()
				#duplicate_notify.write_header(GeneralMsg.GeneralNotify)
				#duplicate_notify.write(c_uint(server.NotifyReason.DuplicateDisconnected))
				#self.send(duplicate_notify, address)

			session_key = hex(random.getrandbits(128))[2:]
			account.address = address
			account.session_key = session_key
			self.conn.transaction_manager.commit()
			redirect_host, redirect_port = await self.address_for_world((0, 0, 0))
		else:
			session_key = ""

		first_time_with_subscription = False # not implemented
		is_ftp = False # not implemented

		response.write(session_key, allocated_length=66)
		response.write(redirect_host.encode("latin1"), allocated_length=33)
		response.write(bytes(33))
		response.write(c_ushort(redirect_port))
		response.write(bytes(35))
		response.write(bytes(36))# b"00000000-0000-0000-0000-000000000000"
		response.write(bytes(1))# possibly terminator of the previous
		response.write(bytes(4))
		response.write(bytes(2))# b"US"
		response.write(bytes(1))# possibly terminator of the previous
		response.write(c_bool(first_time_with_subscription))
		response.write(c_bool(is_ftp))
		response.write(bytes(8))# b"\x99\x0f\x05\x00\x00\x00\x00\x00"
		response.write(c_ushort(0)) # length of custom error message
		response.write(c_uint(4)) # length of remaining bytes including this
		# remaining would be optional debug "stamps"
		self.send(bytes(response), address)


class Account(Persistent):
	def __init__(self, username, password_hash, address):
		self.username = username
		self.password = password_hash
		self.address = address
		self.characters = PersistentMapping()
		self.characters.selected = nothing

# I'd use a lambda but that isn't well handled by the db
def nothing():
	return None
