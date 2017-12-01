import logging

from luserver.world import server
from luserver.interfaces.plugin import ChatCommand

class Filelog(ChatCommand):
	def __init__(self):
		super().__init__("filelog", description="Change which packets are logged to file")
		self.command.add_argument("action", choices=("add", "remove", "show"), default="show")
		self.command.add_argument("packetname", nargs="+")

	def run(self, args, sender):
		args.packetname = " ".join(args.packetname)
		if args.action == "add":
			server.file_logged_packets.add(args.packetname)
		elif args.action == "remove":
			server.file_logged_packets.remove(args.packetname)
		elif args.action == "show":
			server.chat.sys_msg_sender(server.file_logged_packets)

class Log(ChatCommand):
	def __init__(self):
		super().__init__("log", description="Set log level.")
		self.command.add_argument("logger")
		self.command.add_argument("level")

	def run(self, args, sender):
		logging.getLogger(args.logger).setLevel(args.level.upper())
		server.chat.sys_msg_sender("%s set to %s." % (args.logger, args.level))

class NoConsoleLog(ChatCommand):
	def __init__(self):
		super().__init__("noconsolelog", description="Change which packets are logged to console. Adding a packet removes it from logging and vice versa.")
		self.command.add_argument("action", choices=("add", "remove", "show"), default="show")
		self.command.add_argument("packetname")

	def run(self, args, sender):
		if args.action == "add":
			server.not_console_logged_packets.add(args.packetname)
		elif args.action == "remove":
			server.not_console_logged_packets.remove(args.packetname)
		elif args.action == "show":
			server.chat.sys_msg_sender(server.not_console_logged_packets)
