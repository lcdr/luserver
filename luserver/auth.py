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

class LoginError(Exception):
	pass

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
		self.register_handler(AuthServerMsg.LoginRequest, self.on_login_request)

	async def on_login_request(self, request, address):
		return_code = LoginReturnCode.InsufficientAccountPermissions # needed to display error message
		message = ""
		redirect_host, redirect_port = "", 0
		session_key = ""
		try:
			if not self.db.config["auth_enabled"]:
				raise LoginError(self.db.config["auth_disabled_message"])

			self.conn.sync()
			username = request.read(str, allocated_length=33)
			password = request.read(str, allocated_length=41)

			if username not in self.db.accounts:
				raise LoginError(LoginReturnCode.InvalidUsernameOrPassword)
			else:
				if not encryption.verify(password, self.db.accounts[username].password):
					raise LoginError(LoginReturnCode.InvalidUsernameOrPassword)

			account = self.db.accounts[username]

			"""
			if account.address is not None and account.address != address:
				log.info("Disconnecting duplicate at %s", account.address)
				self.close_connection(account.address, server.DisconnectReason.DuplicateLogin)

				duplicate_notify = BitStream()
				duplicate_notify.write_header(GeneralMsg.GeneralNotify)
				duplicate_notify.write(c_uint(server.NotifyReason.DuplicateDisconnected))
				self.send(duplicate_notify, address)
			"""

			session_key = hex(random.getrandbits(128))[2:]
			#account.address = address
			account.session_key = session_key
			self.conn.transaction_manager.commit()
			redirect_host, redirect_port = await self.address_for_world((0, 0, 0))
			log.info("Logging in %s to world %s with key %s", username, (redirect_host, redirect_port), session_key)

		except LoginError as e:
			if isinstance(e.args[0], str):
				message = str(e)
			else:
				return_code = e.args[0]
		except Exception as e:
			import traceback
			traceback.print_exc()
			message = "Server error during login, contact server operator"
		else:
			return_code = LoginReturnCode.Success

		response = BitStream()
		response.write_header(WorldClientMsg.LoginResponse)
		response.write(c_ubyte(return_code))
		response.write(bytes(264))
		# client version
		response.write(c_ushort(1))
		response.write(c_ushort(10))
		response.write(c_ushort(64))

		first_time_with_subscription = False  # not implemented
		is_ftp = False  # not implemented

		response.write(session_key, allocated_length=33)
		response.write(redirect_host.encode("latin1"), allocated_length=33)
		response.write(bytes(33))
		response.write(c_ushort(redirect_port))
		response.write(bytes(35))
		response.write(bytes(36))  # b"00000000-0000-0000-0000-000000000000"
		response.write(bytes(1))  # possibly terminator of the previous
		response.write(bytes(4))
		response.write(bytes(2))  # b"US"
		response.write(bytes(1))  # possibly terminator of the previous
		response.write(c_bool(first_time_with_subscription))
		response.write(c_bool(is_ftp))
		response.write(bytes(8))  # b"\x99\x0f\x05\x00\x00\x00\x00\x00"
		response.write(message, length_type=c_ushort) # custom error message
		response.write(c_uint(4))  # length of remaining bytes including this
		# remaining would be optional debug "stamps"
		self.send(bytes(response), address)

class GMLevel:
	Nothing = 0
	Admin = 1

class Account(Persistent):
	def __init__(self, username, password):
		self.username = username
		self.password = encryption.encrypt(password)
		#self.address = address
		self.muted_until = 0
		self.banned_until = 0
		self.gm_level = GMLevel.Nothing
		self.characters = PersistentMapping()
		self.characters.selected = nothing

# I'd use a lambda but that isn't well handled by the db
def nothing():
	return None
