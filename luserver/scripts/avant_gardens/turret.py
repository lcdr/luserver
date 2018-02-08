import luserver.components.script as script
from luserver.components.rebuild import RebuildState

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.die_callback = self.object.call_later(20, self.die_if_not_building)

	def complete_rebuild(self, player):
		self.object.physics.lock_node_rotation(node_name=b"base")
		self.object.cancel_callback(self.die_callback)

	def die_if_not_building(self):
		if self.object.rebuild.rebuild_state != RebuildState.Building:
			self.object.destructible.simply_die()
