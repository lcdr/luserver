import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.moving_platform.no_autostart = True

	def on_complete_rebuild(self, player):
		self.object.physics.proximity_radius(5)
		self.player = player

	def on_enter(self, player):
		if player == self.player:
			self.player = None
			self.object.moving_platform.start_pathing()
