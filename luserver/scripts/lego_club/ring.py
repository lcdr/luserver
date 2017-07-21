import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object.destructible.simply_die(killer=player, loot_owner=player)
