import luserver.components.script as script

QUICKBUILD_TURRET_LOT = 6254

class ScriptComponent(script.ScriptComponent):
	def on_destruction(self):
		self._v_server.spawn_object(QUICKBUILD_TURRET_LOT, position=self.position, rotation=self.rotation)
