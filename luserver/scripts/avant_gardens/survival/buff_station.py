import luserver.components.script as script

DROPS = {
	# powerup lot: interval
	177: 3, # life
	935: 4, # imagination
	6431: 6} # armor

class ScriptComponent(script.ScriptComponent):
	def complete_rebuild(self, player):
		for powerup, interval in DROPS.items():
			self.object.call_later(interval, self.spawn, powerup, player)

	def spawn(self, powerup, player):
		self.object.physics.drop_loot(powerup, player)
		self.object.call_later(DROPS[powerup], self.spawn, powerup, player)
