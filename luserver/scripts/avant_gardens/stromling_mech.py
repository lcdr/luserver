import luserver.components.script as script
from luserver.world import server

QUICKBUILD_TURRET_LOT = 6254

class ScriptComponent(script.ScriptComponent):
	def on_destruction(self):
		server.spawn_object(QUICKBUILD_TURRET_LOT, {"position": self.object.physics.position, "rotation": self.object.physics.rotation})
