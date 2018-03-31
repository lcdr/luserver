from persistent import Persistent

from ...game_object import Player

class CharSubcomponent(Persistent):
	def __init__(self, player: Player):
		self.object = player
		for name in dir(self):
			if name.startswith("on_"):
				self.object.add_handler(name[3:], getattr(self, name))
