import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_destruction(self) -> None:
		server.get_objects_in_group("SpiderBoss")[0].script.spiderling_defeated()
