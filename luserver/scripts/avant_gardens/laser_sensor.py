import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.active = True

	def on_enter(self, player):
		if self.active:
			self.object.skill.cast_skill(163, target=player)
