from ..bitstream import c_int64, c_ushort
from .component import Component
from .mission import MissionState, TaskType

class CollectibleComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.collectible_id = set_vars.get("collectible_id", 0)

	def serialize(self, out, is_creation):
		out.write(c_ushort(self.collectible_id))

	def has_been_collected(self, address, player_id:c_int64=None):
		player = self.object._v_server.game_objects[player_id]
		# update missions that have this collectible as requirement
		for mission in player.char.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.Collect and task.target == self.object.lot:
						coll_id = self.collectible_id+(self.object._v_server.world_id[0]<<8)
						mission.increment_task(task, player, increment=coll_id)
