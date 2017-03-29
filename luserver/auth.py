import datetime
import logging
import random
import time

try:
	import bcrypt
	from passlib.hash import bcrypt as encryption
except ImportError:
	from passlib.hash import pbkdf2_sha256 as encryption
from persistent import Persistent
from persistent.mapping import PersistentMapping

from . import commonserver
from .bitstream import c_bool, c_ubyte, c_uint, c_ushort, WriteStream
from .messages import AuthServerMsg, WorldClientMsg

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

class AuthServer(commonserver.Server):
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
				log.info("Login attempt with username %s and invalid password", username)
				raise LoginError(LoginReturnCode.InvalidUsernameOrPassword)

			account = self.db.accounts[username]

			if account.gm_level != GMLevel.Admin and account.banned_until > time.time():
				raise LoginError("You have been banned until %s. If you believe this was in error, contact the server operator." % datetime.datetime.fromtimestamp(account.banned_until))

			if account.password_state == PasswordState.AcceptNew:
				if encryption.verify(password, account.password):
					raise LoginError("Password must not be the same as temporary password")
				account.password = encryption.encrypt(password)
				account.password_state = PasswordState.Set
				self.conn.transaction_manager.commit()
				raise LoginError("Password has been set.")

			if not encryption.verify(password, account.password):
				raise LoginError(LoginReturnCode.InvalidUsernameOrPassword)

			if account.password_state == PasswordState.Temp:
				account.password_state = PasswordState.AcceptNew
				self.conn.transaction_manager.commit()
				raise LoginError("Your password is one-use-only.\nSign in again to set the used password as your permanent password.")

			"""
			if account.address is not None and account.address != address:
				log.info("Disconnecting duplicate at %s", account.address)
				self.close_connection(account.address, server.DisconnectReason.DuplicateLogin)

				duplicate_notify = WriteStream()
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
		except Exception:
			import traceback
			traceback.print_exc()
			message = "Server error during login, contact server operator"
		else:
			return_code = LoginReturnCode.Success

		response = WriteStream()
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
	Mod = 50
	Admin = 100

class PasswordState:
	Temp = 0
	AcceptNew = 1
	Set = 2

class Account(Persistent):
	def __init__(self, username, password):
		self.username = username
		self.password = encryption.encrypt(password)
		self.password_state = PasswordState.Set
		#self.address = address
		self.muted_until = 0
		self.banned_until = 0
		self.gm_level = GMLevel.Nothing
		self.characters = PersistentMapping()
		self.characters.selected = nothing

	def set_password(self, password):
		self.password = encryption.encrypt(password)

# I'd use a lambda but that isn't well handled by the db
def nothing():
	return None
