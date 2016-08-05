import code

import transaction
from ZEO.ClientStorage import ClientStorage
from ZODB import DB

db = DB(ClientStorage(("localhost", 12345), wait=False, wait_timeout=0))

conn = db.open()
root = conn.root
c = transaction.commit

def a():
	for acc in root.accounts.values():
		for char in acc.characters.values():
			yield char

def o():
	for world in root.world_data.values():
		for obj in world.objects.values():
			yield obj

def e():
	yield from a()
	yield from o()

v = dict(root._root)
v.update(globals())
code.interact(banner="Enter a database expression", local=v)
