from pyraknet.bitstream import c_bit, c_int64, c_uint, c_ushort
from ..game_object import broadcast, c_int, E
from ..game_object import c_int64 as c_int64_
from ..game_object import c_uint as c_uint_
from .scripted_activity import ScriptedActivityComponent

class RacingNotificationType:
	Invalid = 0
	ActivityStart = 1
	RewardPlayer = 2
	Exit = 3
	Replay = 4
	RemovePlayer = 5
	LeaderboardUpdated = 6

class RacingControlComponent(ScriptedActivityComponent):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.racing_control = self
		self._flags["player_data"] = "player_data_flag"
		self.player_data = {}

	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		out.write(c_bit(True))
		out.write(c_ushort(2))
		out.write(c_bit(self.player_data_flag))
		if self.player_data_flag:
			index = 0
			for player, data in self.player_data.items():
				out.write(c_bit(True))
				out.write(c_int64(player.object_id))
				out.write(c_int64(data[0].object_id))
				out.write(c_uint(index))
				out.write(c_bit(False))
				index += 1
			out.write(c_bit(False))
			self.player_data_flag = False

		out.write(c_bit(True))
		out.write("MainPath", length_type=c_ushort)
		out.write(c_bit(False))

	@broadcast
	def notify_racing_client(self, event_type:c_uint_=RacingNotificationType.Invalid, param1:c_int=E, param_obj:c_int64_=E, param_str:str=E, single_client:c_int64=E):
		pass
