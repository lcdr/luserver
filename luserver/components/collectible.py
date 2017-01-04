from ..bitstream import c_int64, c_ushort
from .component import Component
from .mission import TaskType

class CollectibleComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.collectible_id = set_vars.get("collectible_id", 0)

	def serialize(self, out, is_creation):
		out.write(c_ushort(self.collectible_id))

	def has_been_collected(self, player_id:c_int64=None):
		player = self.object._v_server.game_objects[player_id]
		coll_id = self.collectible_id+(self.object._v_server.world_id[0]<<8)
		player.char.update_mission_task(TaskType.Collect, self.object.lot, increment=coll_id)
