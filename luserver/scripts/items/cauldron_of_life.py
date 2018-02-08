import luserver.scripts.items.spawn_powerups as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		super().init(powerup_lot=177, num_powerups=3, num_cycles=10, cycle_time=20, death_delay=20)
