import luserver.scripts.items.spawn_powerups as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		super().init(powerup_lot=6431, num_powerups=4, num_cycles=8, cycle_time=25, death_delay=25)
