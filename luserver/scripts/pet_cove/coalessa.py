import luserver.components.script as script
from luserver.game_object import c_int_, GameObject

class ScriptComponent(script.ScriptComponent):
	def fire_event_server_side(self, args:str=None, param1:c_int_=-1, param2:c_int_=-1, param3:c_int_=-1, sender:GameObject=None):
		if args == "unlockEmote":
			sender.char.set_emote_lock_state(emote_id=115, lock=False)
