import code

import transaction
import ZEO

from luserver.world import WorldServer

conn = ZEO.connection(12345)
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
