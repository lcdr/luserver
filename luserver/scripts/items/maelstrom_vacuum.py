import luserver.components.script as script
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def fire_event_server_side(self, address, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "attemptCollection":
			player = self.object._v_server.game_objects[self.object.parent]
			sample = self.object._v_server.game_objects[sender_id]
			sample.destructible.deal_damage(1, player)
			self.object._v_server.send_game_message(self.object.play_animation, animation_id="collect_maelstrom", play_immediate=False, address=player.char.address)
