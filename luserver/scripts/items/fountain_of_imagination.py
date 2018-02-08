import luserver.scripts.items.spawn_powerups as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		super().init(powerup_lot=935, num_powerups=5, num_cycles=6, cycle_time=30, death_delay=30)
