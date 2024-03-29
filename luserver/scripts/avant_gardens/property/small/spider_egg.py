import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def spawn_spider(self):
		self.object.render.play_f_x_effect(name=b"test", effect_type="maelstrom", effect_id=2856)
		self.object.render.play_f_x_effect(name=b"dropdustmedium", effect_type="rebuild_medium", effect_id=2260)
		self.object.render.play_f_x_effect(name=b"egg_puff_b", effect_type="create", effect_id=644)
		self.object.call_later(1.8, self.spawn)

	def spawn(self):
		server.spawn_object(16197, {"position": self.object.physics.position, "rotation": self.object.physics.rotation})
		self.object.destructible.simply_die()
