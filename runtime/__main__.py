import asyncio
import configparser
import logging
import os
import sys
import time

import ZEO

from luserver.auth import AuthServer
from luserver.world import WorldServer

config = configparser.ConfigParser()
config.read("luserver.ini")

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

while True:
	try:
		conn = ZEO.connection(12345, wait_timeout=3)
		break
	except ZEO.Exceptions.ClientDisconnected:
		os.system(r"start /d db runzeo -a 12345 -f ./server_db.db")
		time.sleep(3)

try:
	if len(sys.argv) == 1:
		AuthServer(config["connection"]["internal_host"], max_connections=8, db_conn=conn)
	else:
		world_id = int(sys.argv[1]), int(sys.argv[2])
		if len(sys.argv) == 4:
			port = int(sys.argv[3])
		else:
			port = 0
		WorldServer((config["connection"]["internal_host"], port), config["connection"]["external_host"], world_id, max_connections=8, db_conn=conn)

	loop = asyncio.get_event_loop()
	loop.run_forever()
	loop.close()
except Exception:
	import traceback
	traceback.print_exc()
	time.sleep(5)
