import luserver.components.script as script
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def fire_event_server_side(self, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "unlockEmote":
			sender = self.object._v_server.game_objects[sender_id]
			sender.char.set_emote_lock_state(emote_id=115, lock=False)
