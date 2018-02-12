import luserver.components.script as script
from luserver.game_object import c_int, EP, ES, Player

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.render.play_animation("idle_maelstrom")

	def on_fire_event_server_side(self, player, args:str=ES, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:Player=EP):
		if args == "attemptCollection":
			sample = sender
			sample.destructible.deal_damage(1, player)
			self.object.render.play_animation("collect_maelstrom")
