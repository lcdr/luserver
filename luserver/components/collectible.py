from pyraknet.bitstream import c_ushort
from ..game_object import E, Player
from ..world import server
from .component import Component
from .mission import TaskType

class CollectibleComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._collectible_id = set_vars.get("collectible_id", 0)

	def serialize(self, out, is_creation):
		out.write(c_ushort(self._collectible_id))

	def has_been_collected(self, player:Player=E):
		coll_id = self._collectible_id + (server.world_id[0] << 8)
		player.char.update_mission_task(TaskType.Collect, self.object.lot, increment=coll_id)
