"""
Modification of pyraknet.__main__ manual server, with number sorting for packet names and send delays. I guess that could also be included by default in pyraknet.__main__ .
Mostly intended for manually replaying captures.
"""
import asyncio
import logging
import os
import re
import threading
import time
import traceback

import pyraknet.server

from luserver.bitstream import c_uint, c_ushort
from luserver.messages import msg_enum, GameMessage, Message, WorldClientMsg, WorldServerMsg
from luserver.modules.mail import MailID

logging.basicConfig(format="%(levelname).1s:%(message)s", level=logging.DEBUG)

try:
	import colorlog
except ImportError:
	pass
else:
	handler = colorlog.StreamHandler()
	handler.setFormatter(colorlog.ColoredFormatter("%(log_color)s%(levelname).1s:%(message)s"))

	logger = logging.getLogger()
	logger.handlers[0] = handler


def atoi(text):
	return int(text) if text.isdigit() else text

def natural_keys(text):
	return [atoi(c) for c in re.split(r"(\d+)", text)]

class Server(pyraknet.server.Server):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		print("Enter packet directory path to send packets in directory")
		command_line = threading.Thread(target=self.input_loop, daemon=True) # I'd like to do this with asyncio but I can't figure out how
		command_line.start()

	def input_loop(self):
		while True:
			try:
				path = os.path.normpath(os.path.join(__file__, "..", "packets", input()))
				files = os.listdir(path)
				files.sort(key=natural_keys)
				for file in files:
					if os.path.isfile(path+"/"+file):
						with open(path+"/"+file, "rb") as content:
							print("sending", file)
							self.send(content.read(), broadcast=True)
							time.sleep(0.3)
			except OSError:
				traceback.print_exc()

	def packetname(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
				data = b"\x53"+data[12:]
			if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.GameMessage):
				message_name = GameMessage(c_ushort.unpack(data[16:18])[0]).name
				return "GameMessage/" + message_name
			if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.Mail) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.Mail):
				packetname = MailID(c_uint.unpack(data[8:12])[0]).name
				return "Mail/" + packetname
			return msg_enum[data[1]](data[3]).name
		return super().packetname(data)

	def unknown_packetname(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
				data = b"\x53"+data[12:]
			if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.GameMessage):
				return "GameMessage/%i" % c_ushort.unpack(data[16:18])[0]
			return msg_enum[data[1]].__name__ + "/%.2x" % data[3]
		return super().unknown_packetname(data)

	def packet_id(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
				return data[12], data[14]
			return data[1], data[3]
		return super().packet_id(data)

	def handler_data(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
				return data[19:]
			return data[8:]
		return super().handler_data(data)


if __name__ == "__main__":
	print("Enter server port")
	port = int(input())
	Server(("localhost", port), max_connections=10, incoming_password=b"3.25 ND1")

	loop = asyncio.get_event_loop()
	loop.run_forever()
	loop.close()
