import luserver.components.script as script
from luserver.game_object import c_int_, c_int64_, GameObject, single


class ScriptComponent(script.ScriptComponent):
	# hacky workaround incoming:
	# the clientside implementation is broken and doesn't check the sender param
	# so the cinematic would get displayed for everyone since this message is broadcast
	# easiest fix is to override it for this script to be single instead
	# other option would be to allow broadcast messages to be single per-call, but that seems like even more of a hack
	@single
	def fire_event_client_side(self, args:str=None, obj:GameObject=None, param1:c_int64_=0, param2:c_int_=-1, sender:GameObject=None):
		pass
