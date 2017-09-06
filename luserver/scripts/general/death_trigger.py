import luserver.components.script as script
from luserver.components.destructible import KillType

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.simply_die(kill_type=KillType.Silent, killer=self.object)
