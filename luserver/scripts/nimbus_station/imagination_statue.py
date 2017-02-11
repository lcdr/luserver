import luserver.components.script as script

IMAGINATION_POWERUP_LOT = 935
SPAWN_AMOUNT = 10
SPAWN_INTERVAL = 1.5

class ScriptComponent(script.ScriptComponent):
	def complete_rebuild(self, player):
		for i in range(SPAWN_AMOUNT):
			self.object.call_later(i*SPAWN_INTERVAL, self.object.physics.drop_loot, IMAGINATION_POWERUP_LOT, player)
