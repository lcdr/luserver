import luserver.components.script as script

IMAGINATION_SKILL = 13

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object.skill.cast_skill(13, target=player)
		self.object.destructible.simply_die(killer=self.object, loot_owner=self.object)
