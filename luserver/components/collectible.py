from ..bitstream import c_int64, c_ushort
from .mission import MissionState, TaskType

class CollectibleComponent:
	def __init__(self, comp_id):
		pass

	def serialize(self, out, is_creation):
		out.write(c_ushort(0)) # todo

	def has_been_collected(self, address, player_id:c_int64=None):
		player = self._v_server.game_objects[player_id]
		# update missions that have this collectible as requirement
		for mission in player.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.Collect and task.target == self.lot:
						mission.increment_task(task, self._v_server, player)
