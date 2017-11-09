import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def init(self, powerup_lot, num_powerups, num_cycles, cycle_time, death_delay):
		self.powerup_lot = powerup_lot
		self.num_powerups = num_powerups
		self.num_cycles = num_cycles
		self.cycle_time = cycle_time
		self.death_delay = death_delay
		self.current_cycle = 0
		self.object.call_later(1.5, self.spawn)

	def spawn(self):
		self.current_cycle += 1
		for _ in range(self.num_powerups):
			self.object.physics.drop_loot(self.powerup_lot, server.game_objects[self.object.parent])
		if self.current_cycle < self.num_cycles:
			self.object.call_later(self.cycle_time, self.spawn)
		else:
			self.object.call_later(self.death_delay, self.object.destructible.simply_die)
