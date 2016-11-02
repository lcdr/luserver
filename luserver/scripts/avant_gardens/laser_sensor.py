import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object.skill.cast_skill(163, target=player)
