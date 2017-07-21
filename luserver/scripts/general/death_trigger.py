import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.simply_die(kill_type=1, killer=self.object)
