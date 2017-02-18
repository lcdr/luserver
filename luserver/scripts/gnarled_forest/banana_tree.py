import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object._v_server.spawn_object(6909, {"position": self.object.physics.position, "rotation": self.object.physics.rotation})
