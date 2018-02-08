from pyraknet.bitstream import c_ushort, WriteStream
from ..game_object import Config, EP, GameObject, Player
from ..world import server
from .component import Component
from .mission import TaskType

class CollectibleComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self._collectible_id = set_vars.get("collectible_id", 0)

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_ushort(self._collectible_id))

	def has_been_collected(self, player:Player=EP) -> None:
		coll_id = self._collectible_id + (server.world_id[0] << 8)
		player.char.update_mission_task(TaskType.Collect, self.object.lot, increment=coll_id)
