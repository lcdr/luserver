import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		sensor = self.object._v_server.get_objects_in_group(self.script_vars["volume_group"])[0]
		sensor.script.active = True

	def on_destruction(self):
		sensor = self.object._v_server.get_objects_in_group(self.script_vars["volume_group"])[0]
		sensor.script.active = False
