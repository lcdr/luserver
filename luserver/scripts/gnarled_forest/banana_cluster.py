import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		# bananas go bad after a while
		self.object.call_later(100, self.object.destructible.simply_die)
