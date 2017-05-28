import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_destruction(self):
		self.object._v_server.get_objects_in_group("SpiderBoss")[0].script.spiderling_defeated()
