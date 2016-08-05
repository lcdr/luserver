"""
Modification of pyraknet.__main__ manual server, with number sorting for packet names and send delays. I guess that could also be included by default in pyraknet.__main__ .
Mostly intended for manually replaying captures.
"""
import asyncio
import os
import re
import threading
import time
import traceback

import pyraknet.server

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
				path = "./packets/"+input()
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

if __name__ == "__main__":
	print("Enter server port")
	port = int(input())
	Server(("localhost", port), max_connections=10, incoming_password=b"3.25 ND1")

	loop = asyncio.get_event_loop()
	loop.run_forever()
	loop.close()
