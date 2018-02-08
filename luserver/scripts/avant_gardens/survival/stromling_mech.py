import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.stats.faction = 4
