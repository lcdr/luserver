import luserver.components.script as script
from luserver.game_object import c_int, EP, ES, Player

class ScriptComponent(script.ScriptComponent):
	def on_fire_event_server_side(self, args:str=ES, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:Player=EP):
		if args == "unlockEmote":
			sender.char.set_emote_lock_state(emote_id=115, lock=False)
