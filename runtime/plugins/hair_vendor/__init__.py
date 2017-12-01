from luserver.world import server

class HairVendor:
	def __init__(self):
		server.add_handler("spawn", self.on_spawn)

	def on_spawn(self, obj):
		if obj.lot == 3925:
			new_items = 3368, 3825, 6496, 6497, 6498, 7113, 8109, 8522, 9791, 10133, 10155, 12091, 12092, 13301, 13331, 13337, 13342, 13346, 13347, 13352, 13357, 13389, 13390, 14083, 14730
			for item in new_items:
				obj.vendor.items_for_sale.append((item, 0, 10))

HairVendor()
