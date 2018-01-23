import luserver.components.script as script
from luserver.game_object import c_int_, GameObject

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.render.play_animation("idle_maelstrom")

	def fire_event_server_side(self, player, args:str=None, param1:c_int_=-1, param2:c_int_=-1, param3:c_int_=-1, sender:GameObject=None):
		if args == "attemptCollection":
			sample = sender
			sample.destructible.deal_damage(1, player)
			self.object.render.play_animation("collect_maelstrom")
