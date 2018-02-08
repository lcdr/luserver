import luserver.components.script as script

INTERACT_RADIUS = 10

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.physics.proximity_radius(INTERACT_RADIUS)

	def on_enter(self, player):
		self.object.render.play_animation("fly1", play_immediate=True, priority=4)
		self.object.call_later(1, lambda: self.object.destructible.simply_die(killer=player))
