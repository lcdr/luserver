import luserver.components.script as script
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def fire_event_server_side(self, address, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "unlockEmote":
			sender = self._v_server.game_objects[sender_id]
			self._v_server.send_game_message(sender.set_emote_lock_state, emote_id=115, lock=False, address=address)
