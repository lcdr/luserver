import asyncio
import datetime
import logging
import math
import os
import re
import secrets
import time
from typing import cast

from bitstream import c_bool, c_ushort
from luserver.auth import Account, GMLevel, PasswordState
from luserver.bitstream import WriteStream
from luserver.game_object import Player
from luserver.ldf import LDF, LDFDataType
from luserver.messages import WorldClientMsg
from luserver.world import Event, server
from luserver.components.physics import AABB, CollisionSphere, PrimitiveModelType
from luserver.interfaces.plugin import ChatCommand, normal_bool
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3

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
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("player")
		self.command.add_argument("--minutes", type=int, default=0)
		self.command.add_argument("--hours", type=int, default=0)
		self.command.add_argument("--days", type=int, default=0)
		self.command.add_argument("--weeks", type=int, default=0)

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.lot == 1 and obj.name == args.player:
				obj = cast(Player, obj)
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

		sender.char.ui.disp_message_box("Account %s created. Temp password %s.\nSave this password somewhere, this is the only time it will be shown." % (args.username, temp_password))

class Kick(ChatCommand):
	def __init__(self):
		super().__init__("kick")
		self.command.add_argument("player")

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.lot == 1 and obj.name == args.player:
				server.close_connection(cast(Player, obj).char.address)
				break
		else:
			server.chat.sys_msg_sender("Player not connected")

class Mute(ChatCommand):
	def __init__(self):
		super().__init__("mute")
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("player")
		self.command.add_argument("--minutes", type=int, default=0)
		self.command.add_argument("--hours", type=int, default=0)
		self.command.add_argument("--days", type=int, default=0)
		self.command.add_argument("--weeks", type=int, default=0)

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.lot == 1 and obj.name == args.player:
				mute_duration = datetime.timedelta(args.days, 0, 0, 0, args.minutes, args.hours, args.weeks)
				muted_until = time.time() + mute_duration.total_seconds()
				server.chat.sys_msg_sender("Player will be muted until %s" % datetime.datetime.fromtimestamp(muted_until))
				cast(Player, obj).char.account.muted_until = muted_until
				break
		else:
			server.chat.sys_msg_sender("Player not connected")

class PhysicsDebug(ChatCommand):
	def __init__(self):
		super().__init__("physicsdebug")
		self.debug_markers = []
		server.add_handler(Event.ProximityRadius, self.on_proximity_radius)

	def run(self, args, sender):
		if self.debug_markers:
			for marker in self.debug_markers:
				server.replica_manager.destruct(marker)
			self.debug_markers.clear()
		else:
			for obj in server.general.tracked_objects.copy():
				self.spawn_debug_marker(obj)

	def on_proximity_radius(self, obj):
		if not self.debug_markers:
			return
		self.spawn_debug_marker(obj)

	def spawn_debug_marker(self, obj):
		coll = server.general.tracked_objects[obj]
		set_vars = {"parent": obj, "rotation": Quaternion.identity}
		if isinstance(coll, AABB):
			config = LDF()
			config.ldf_set("primitiveModelType", LDFDataType.INT32, PrimitiveModelType.Cuboid)
			config.ldf_set("primitiveModelValueX", LDFDataType.FLOAT, coll.max.x-coll.min.x)
			config.ldf_set("primitiveModelValueY", LDFDataType.FLOAT, coll.max.y-coll.min.y)
			config.ldf_set("primitiveModelValueZ", LDFDataType.FLOAT, coll.max.z-coll.min.z)

			set_vars["position"] = Vector3((coll.min.x+coll.max.x)/2, coll.min.y, (coll.min.z+coll.max.z)/2)
			set_vars["config"] = config
			marker = server.spawn_object(14510, set_vars)
		elif isinstance(coll, CollisionSphere):
			set_vars["position"] = coll.position
			set_vars["scale"] = math.sqrt(coll.sq_radius)/5
			marker = server.spawn_object(6548, set_vars)
		else:
			raise TypeError(coll)
		self.debug_markers.append(marker)

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

		sender.char.ui.disp_message_box("Password reset for %s. Temp password %s.\nSave this password somewhere, this is the only time it will be shown." % (args.username, temp_password))

class Restart(ChatCommand):
	def __init__(self):
		super().__init__("restart", aliases=("r",))
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("--show_message", action="store_true")

	def run(self, args, sender):
		asyncio.ensure_future(self.do_restart(args, sender))

	async def do_restart(self, args, sender):
		server.conn.transaction_manager.commit()
		for obj in server.game_objects.values():
			if obj.lot == 1:
				conn = obj.char.data()["conn"]
				server_address = await server.address_for_world(server.world_id, conn.get_type(), include_self=False)
				log.info("Sending redirect to world %s", server_address)
				redirect = WriteStream()
				redirect.write_header(WorldClientMsg.Redirect)
				redirect.write(server_address[0].encode("latin1"), allocated_length=33)
				redirect.write(c_ushort(server_address[1]))
				redirect.write(c_bool(args.show_message))
				conn.send(redirect)
		await asyncio.sleep(5)
		server.shutdown()

class Send(ChatCommand):
	def __init__(self):
		super().__init__("send", description="This will manually send packets")
		self.command.add_argument("directory", help="Name of subdirectory of ./packets/ which contains the packets you want to send")

	def run(self, args, sender):
		path = os.path.normpath(os.path.join(__file__, "..", "..", "..", "packets", args.directory))
		files = os.listdir(path)
		files.sort(key=lambda text: [int(text) if text.isdigit() else text for c in re.split(r"(\d+)", text)]) # sort using numerical values
		for file in files:
			with open(os.path.join(path, file), "rb") as content:
				server.chat.sys_msg_sender("sending "+str(file))
				data = content.read()
				#if data[:4] == b"\x53\x05\x00\x0c":
				#	data = data[:8] + bytes(c_int64(sender.object_id)) + data[16:]
				sender.char.data()["conn"].send(data)

class SetGMLevel(ChatCommand):
	def __init__(self):
		super().__init__("setgmlevel")
		self.command.add_argument("player")
		self.command.add_argument("level", type=int)

	def run(self, args, sender):
		if args.level >= sender.char.account.gm_level:
			server.chat.sys_msg_sender("Can't set level higher or equal to your own")
			return
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
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("player")

	def run(self, args, sender):
		with server.multi:
			player = server.find_player_by_name(args.player)
			player.char.account.banned_until = 0

		server.chat.sys_msg_sender("%s has been unbanned." % args.player)

class Unmute(ChatCommand):
	def __init__(self):
		super().__init__("unmute")
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("player")

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.lot == 1 and obj.name == args.player:
				cast(Player, obj).char.account.muted_until = 0
				server.chat.sys_msg_sender("%s has been unmuted." % args.player)
				break
		else:
			server.chat.sys_msg_sender("Player not connected")
