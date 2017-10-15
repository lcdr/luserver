import asyncio
import datetime
import logging
import os
import re
import secrets
import time

from ..auth import Account, PasswordState
from ..bitstream import BitStream, c_bool, c_ushort
from ..messages import WorldClientMsg
from ..world import server
from .command import ChatCommand, normal_bool

log = logging.getLogger(__name__)

class Auth(ChatCommand):
	def __init__(self):
		super().__init__("auth")
		self.command.add_argument("enabled", type=normal_bool)
		self.command.add_argument("--message", nargs="+")

	def run(self, args, sender):
		with server.multi:
			server.db.config["auth_enabled"] = args.enabled
			server.chat.sys_msg_sender("Auth is now %s" % args.enabled)
			if args.message is not None:
				server.db.config["auth_disabled_message"] = " ".join(args.message)

class Ban(ChatCommand):
	def __init__(self):
		super().__init__("ban")
		self.command.add_argument("player")
		self.command.add_argument("--minutes", type=int, default=0)
		self.command.add_argument("--hours", type=int, default=0)
		self.command.add_argument("--days", type=int, default=0)
		self.command.add_argument("--weeks", type=int, default=0)

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.name == args.player:
				ban_duration = datetime.timedelta(args.days, 0, 0, 0, args.minutes, args.hours, args.weeks)
				banned_until = time.time() + ban_duration.total_seconds()
				server.chat.sys_msg_sender("Player will be banned until %s" % datetime.datetime.fromtimestamp(banned_until))
				obj.char.account.banned_until = banned_until
				break
		else:
			server.chat.sys_msg_sender("Player not connected")

class CheckForLeaks(ChatCommand):
	def __init__(self):
		super().__init__("checkforleaks")

	def run(self, args, sender):
		sender.char.check_for_leaks(fullcheck=True)

class Commit(ChatCommand):
	def __init__(self):
		super().__init__("commit")

	def run(self, args, sender):
		server.commit()

class CreateAccount(ChatCommand):
	def __init__(self):
		super().__init__("createaccount")
		self.command.add_argument("username")

	def run(self, args, sender):
		if args.username in server.db.accounts:
			raise RuntimeError("Account already exists")
		temp_password = secrets.token_urlsafe(10)

		with server.multi:
			server.db.accounts[args.username] = Account(args.username, temp_password)
			server.db.accounts[args.username].password_state = PasswordState.Temp

		sender.char.disp_message_box("Account %s created. Temp password %s.\nSave this password somewhere, this is the only time it will be shown." % (args.username, temp_password))

class Kick(ChatCommand):
	def __init__(self):
		super().__init__("kick")
		self.command.add_argument("player")

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.name == args.player:
				server.close_connection(obj.char.address)
				break
		else:
			server.chat.sys_msg_sender("Player not connected")

class Mute(ChatCommand):
	def __init__(self):
		super().__init__("mute")
		self.command.add_argument("player")
		self.command.add_argument("--minutes", type=int, default=0)
		self.command.add_argument("--hours", type=int, default=0)
		self.command.add_argument("--days", type=int, default=0)
		self.command.add_argument("--weeks", type=int, default=0)

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.name == args.player:
				mute_duration = datetime.timedelta(args.days, 0, 0, 0, args.minutes, args.hours, args.weeks)
				muted_until = time.time() + mute_duration.total_seconds()
				server.chat.sys_msg_sender("Player will be muted until %s" % datetime.datetime.fromtimestamp(muted_until))
				obj.char.account.muted_until = muted_until
				break
		else:
			server.chat.sys_msg_sender("Player not connected")

class ResetPassword(ChatCommand):
	def __init__(self):
		super().__init__("resetpassword")
		self.command.add_argument("username")

	def run(self, args, sender):
		if args.username not in server.db.accounts:
			raise RuntimeError("Account doesn't exist")
		temp_password = secrets.token_urlsafe(10)

		with server.multi:
			server.db.accounts[args.username].set_password(temp_password)
			server.db.accounts[args.username].password_state = PasswordState.Temp

		sender.char.disp_message_box("Password reset for %s. Temp password %s.\nSave this password somewhere, this is the only time it will be shown." % (args.username, temp_password))

class Restart(ChatCommand):
	def __init__(self):
		super().__init__("restart", aliases=("r",))
		self.command.add_argument("--show_message", action="store_true")

	def run(self, args, sender):
		asyncio.ensure_future(self.do_restart(args, sender))

	async def do_restart(self, args, sender):
		server.conn.transaction_manager.commit()
		server_address = await server.address_for_world(server.world_id, include_self=False)
		log.info("Sending redirect to world %s", server_address)
		redirect = BitStream()
		redirect.write_header(WorldClientMsg.Redirect)
		redirect.write(server_address[0].encode("latin1"), allocated_length=33)
		redirect.write(c_ushort(server_address[1]))
		redirect.write(c_bool(args.show_message))
		for address in server.accounts:
			server.send(redirect, address)
		await asyncio.sleep(5)
		server.shutdown()

class Send(ChatCommand):
	def __init__(self):
		super().__init__("send", description="This will manually send packets")
		self.command.add_argument("directory", help="Name of subdirectory of ./packets/ which contains the packets you want to send")
		self.command.add_argument("--address")
		self.command.add_argument("--broadcast", action="store_true", default=False)

	def run(self, args, sender):
		if not args.broadcast and args.address is None:
			args.address = sender.char.address

		path = os.path.normpath(os.path.join(__file__, "..", "..", "..", "runtime", "packets", args.directory))
		files = os.listdir(path)
		files.sort(key=lambda text: [int(text) if text.isdigit() else text for c in re.split(r"(\d+)", text)]) # sort using numerical values
		for file in files:
			with open(os.path.join(path, file), "rb") as content:
				server.chat.sys_msg_sender("sending "+str(file))
				data = content.read()
				#if data[:4] == b"\x53\x05\x00\x0c":
				#	data = data[:8] + bytes(c_int64(sender.object_id)) + data[16:]
				server.send(data, args.address, args.broadcast)

class SetGMLevel(ChatCommand):
	def __init__(self):
		super().__init__("setgmlevel")
		self.command.add_argument("player")
		self.command.add_argument("level", type=int)

	def run(self, args, sender):
		player = server.find_player_by_name(args.player)
		if player is None:
			server.chat.sys_msg_sender("player cannot be found: %s" % args.player)
			return
		if player == sender and args.level == 0:
			server.chat.sys_msg_sender("You don't want to lose privileges. To appear as a player, use /showgmstatus off")
			return
		player.char.account.gm_level = args.level

class Shutdown(ChatCommand):
	def __init__(self):
		super().__init__("shutdown")

	def run(self, args, sender):
		server.shutdown()

class Unban(ChatCommand):
	def __init__(self):
		super().__init__("unban")
		self.command.add_argument("player")

	def run(self, args, sender):
		with server.multi:
			player = server.find_player_by_name(args.player)
			player.char.account.banned_until = 0

		server.chat.sys_msg_sender("%s has been unbanned." % args.player)

class Unmute(ChatCommand):
	def __init__(self):
		super().__init__("unmute")
		self.command.add_argument("player")

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.name == args.player:
				obj.char.account.muted_until = 0
				server.chat.sys_msg_sender("%s has been unmuted." % args.player)
				break
		else:
			server.chat.sys_msg_sender("Player not connected")
