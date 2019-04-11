import asyncio
import logging
import os
import subprocess
import ssl
import sys
import time

import toml
import ZEO

from pyraknet.transports.abc import ConnectionType
from luserver.auth import AuthServer
from luserver.world import WorldServer

with open(os.path.normpath(os.path.join(__file__, "..", "instance.toml"))) as file:
	config = toml.load(file)

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


if len(sys.argv) == 1:
	instance_id = "auth"
else:
	instance_id = sys.argv[1]+" "+sys.argv[2]

log_path = os.path.normpath(os.path.join(__file__, "..", "logs", "luserver %s.log" % instance_id))
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s"))
logging.getLogger().addHandler(file_handler)

#logging.getLogger().handlers[0].addFilter(logging.Filter("luserver"))
logging.getLogger("ZEO").setLevel(logging.WARNING)
logging.getLogger("txn").setLevel(logging.WARNING)
logging.getLogger("luserver.components.skill").setLevel(logging.INFO)

log = logging.getLogger(__file__)

while True:
	try:
		conn = ZEO.connection(12345, wait_timeout=3)
		break
	except ZEO.Exceptions.ClientDisconnected:
		if os.name == "nt":
			flags = subprocess.CREATE_NEW_CONSOLE
		else:
			flags = 0
		subprocess.Popen("runzeo -a 12345 -f "+os.path.normpath(os.path.join(__file__, "..", "db", "server_db.db")), shell=True, creationflags=flags)
		time.sleep(3)

if "ssl_cert_file" in config["connection"] and "ssl_key_file" in config["connection"]:
	context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
	context.load_cert_chain(config["connection"]["ssl_cert_file"], config["connection"]["ssl_key_file"])
else:
	context = None

if len(sys.argv) == 1:
	a = AuthServer(config["connection"]["internal_host"], max_connections=8, db_conn=conn, ssl=context)
else:
	world_id = int(sys.argv[1]), int(sys.argv[2])
	if len(sys.argv) == 4:
		port = int(sys.argv[3])
	else:
		if config["connection"]["port_range"]:
			range_start, range_stop = config["connection"]["port_range"]
			for port in range(range_start, range_stop):
				for conns in conn.root.servers.values():
					if conns[ConnectionType.RakNet] == (config["connection"]["external_host"], port):
						break
				else:
					log.info("Using port %i", port)
					break
			else:
				log.error("No open port left!")
				sys.exit()
		else:
			port = 0
	WorldServer((config["connection"]["internal_host"], port), config["connection"]["external_host"], world_id, max_connections=8, db_conn=conn, ssl=context)

loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()
