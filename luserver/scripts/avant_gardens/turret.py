import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def complete_rebuild(self, player):
		self.object.physics.lock_node_rotation(node_name="base")
