import luserver.components.script as script
from luserver.world import server
from luserver.components.destructible import KillType
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.banana = None
		self.spawn_banana()

	def spawn_banana(self):
		if self.banana is None:
			self.banana = server.spawn_object(6909, {"position": self.banana_pos(), "rotation": self.object.physics.rotation})
			self.banana.add_handler("on_death", self.on_banana_death)

	def on_hit(self, damage, attacker):
		self.object.stats.life = self.object.stats.max_life # indestructible
		if self.banana is not None:
			self.banana.destructible.simply_die(kill_type=KillType.Silent, killer=self.object)
			self.banana = None
			falling_banana = server.spawn_object(6718, {"position": self.banana_pos(), "rotation": self.object.physics.rotation})
			falling_banana.add_handler("on_death", self.on_banana_death)

	def banana_pos(self):
		offset = Vector3(-5, 12, 0)
		pos = self.object.physics.position
		return pos + self.object.physics.rotation.rotate(offset)

	def on_banana_death(self, banana, killer):
		if killer != self.object:
			self.object.call_later(30, self.spawn_banana)
