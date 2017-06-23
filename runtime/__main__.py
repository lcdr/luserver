import asyncio
import configparser
import logging
import os
import subprocess
import sys
import time

import ZEO

from luserver.auth import AuthServer
from luserver.world import WorldServer

config = configparser.ConfigParser()
config.read(os.path.normpath(os.path.join(__file__, "..", "luserver.ini")))

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

if len(sys.argv) == 1:
	AuthServer(config["connection"]["internal_host"], max_connections=8, db_conn=conn)
else:
	world_id = int(sys.argv[1]), int(sys.argv[2])
	if len(sys.argv) == 4:
		port = int(sys.argv[3])
	else:
		if config["connection"]["port_range"]:
			port_range = config["connection"]["port_range"]
			range_start, range_stop = [int(i) for i in port_range.split(",")]
			for port in range(range_start, range_stop):
				if (config["connection"]["external_host"], port) not in conn.root.servers:
					log.info("Using port %i", port)
					break
			else:
				log.error("No open port left!")
				sys.exit()
		else:
			port = 0
	WorldServer((config["connection"]["internal_host"], port), config["connection"]["external_host"], world_id, max_connections=8, db_conn=conn)

loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()
