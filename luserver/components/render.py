from pyraknet.bitstream import c_float, c_int, c_int64, c_ubyte, c_uint
from ..game_object import broadcast, E, GameObject
from ..game_object import c_int as c_int_
from ..game_object import c_int64 as c_int64_
from .component import Component

class RenderComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.render = self
		self.effects = {}

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_uint(len(self.effects)))
			for name, effect_values in self.effects.items():
				effect_id, effect_type = effect_values
				out.write(c_ubyte(len(name)))
				out.write(name)
				out.write(c_int(effect_id))
				out.write(effect_type, length_type=c_ubyte)
				out.write(c_float(1))
				out.write(c_int64(0))

	def on_destruction(self):
		self.effects.clear()

	@broadcast
	def play_animation(self, animation_id:str=E, expect_anim_to_exist:bool=True, play_immediate:bool=False, trigger_on_complete_msg:bool=False, priority:float=2, scale:float=1):
		pass

	@broadcast
	def play_f_x_effect(self, effect_id:c_int_=-1, effect_type:str=E, scale:float=1, name:bytes=E, priority:float=1, secondary:c_int64_=0, serialize:bool=True):
		self.effects[name] = effect_id, effect_type

	@broadcast
	def stop_f_x_effect(self, kill_immediate:bool=False, name:bytes=E):
		if name in self.effects:
			del self.effects[name]

	@broadcast
	def play_embedded_effect_on_all_clients_near_object(self, effect_name:str=E, from_object:GameObject=E, radius:float=E):
		pass

	@broadcast
	def play_n_d_audio_emitter(self, callback_message_data:c_int64_=0, emitter_id:c_int_=0, event_guid:bytes=E, meta_event_name:bytes=E, result:bool=False, target_object_id_for_ndaudio_callback_messages:c_int64_=0):
		pass

	@broadcast
	def freeze_animation(self, do_freeze:bool=E, duration:float=-1, startup_delay:float=0):
		pass
