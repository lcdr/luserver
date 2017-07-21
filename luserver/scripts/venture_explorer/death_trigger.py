import luserver.components.script as script

DEATH_ANIMATION = "electro-shock-death"

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.simply_die(death_type=DEATH_ANIMATION, killer=self.object)
