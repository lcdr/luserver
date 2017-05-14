import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_destruction(self):
		self.object._v_server.world_control_object.script.on_spider_defeated()
