import asyncio
import logging
import os
import re

from ..bitstream import BitStream, c_bool, c_int64, c_ushort
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
		server.conn.transaction_manager.commit()
		server.db.config["auth_enabled"] = args.enabled
		server.chat.sys_msg_sender("Auth is now %s" % args.enabled)
		if args.message is not None:
			server.db.config["auth_disabled_message"] = " ".join(args.message)
		server.conn.transaction_manager.commit()

class CheckForLeaks(ChatCommand):
	def __init__(self):
		super().__init__("checkforleaks")

	def run(self, args, sender):
		sender.char.check_for_leaks(fullcheck=True)

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

class Shutdown(ChatCommand):
	def __init__(self):
		super().__init__("shutdown")

	def run(self, args, sender):
		server.shutdown()
