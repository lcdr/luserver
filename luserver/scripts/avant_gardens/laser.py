import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		sensor = server.get_objects_in_group(self.script_vars["volume_group"])[0]
		sensor.script.active = True

	def on_destruction(self) -> None:
		sensor = server.get_objects_in_group(self.script_vars["volume_group"])[0]
		sensor.script.active = False
