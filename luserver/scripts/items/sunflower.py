import luserver.scripts.items.spawn_powerups as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		super().init(powerup_lot=11910, num_powerups=4, num_cycles=6, cycle_time=5, death_delay=30)
