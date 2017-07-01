import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		server.spawn_object(6909, {"position": self.object.physics.position, "rotation": self.object.physics.rotation})
