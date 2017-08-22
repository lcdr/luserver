import luserver.components.script as script
from luserver.world import server
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.banana = None
		self.spawn_banana()

	def spawn_banana(self):
		if self.banana is None:
			self.banana = server.spawn_object(6909, {"position": self.banana_pos(), "rotation": self.object.physics.rotation})
			self.banana.add_handler("on_destrucition", self.on_banana_death)

	def on_hit(self, damage, attacker):
		self.object.stats.life = self.object.stats.max_life # indestructible
		if self.banana is not None:
			self.banana.destructible.simply_die()
			self.banana = None
			falling_banana = server.spawn_object(6718, {"position": self.banana_pos(), "rotation": self.object.physics.rotation})
			falling_banana.add_handler("on_destruction", self.on_banana_death)

	def banana_pos(self):
		offset = Vector3(-5, 12, 0)
		pos = self.object.physics.position
		return pos + offset.rotated(self.object.physics.rotation)

	def on_banana_death(self, banana, damage, attacker):
		self.object.call_later(30, self.spawn_banana)
