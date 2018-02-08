from typing import Optional

from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import CallbackID, Config, GameObject, Player
from ..world import server
from ..math.quaternion import Quaternion
from .component import Component
from .skill import BehaviorTemplate

UPDATE_INTERVAL = 1 # todo: make interval skill-dependent

class BaseCombatAIComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.ai = self
		self._flags["target"] = "ai_flag"
		self.skill_range = 7
		self.target = None
		self._enabled = False
		self.update_handle: Optional[CallbackID] = None
		self.object.add_handler("rebuild_init", self._on_rebuild_init)
		self.object.add_handler("complete_rebuild", self._on_rebuild_complete)

	def on_startup(self) -> None:
		if not hasattr(self.object, "skill"):
			return
		if self.object.skill.skills:
			behavior = server.db.skill_behavior[self.object.skill.skills[0]][0]
			assert behavior.template == BehaviorTemplate.NPCCombatSkill
			self.skill_range = min(behavior.max_range, 10)
		self.object.physics.proximity_radius(self.skill_range)

		self._enabled = True

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))

	def _on_rebuild_init(self, _obj: GameObject) -> None:
		self._enabled = False

	def _on_rebuild_complete(self, _obj: GameObject, player: Player) -> None:
		self._enabled = True

	def _disable(self) -> None:
		self._enabled = False
		if self.update_handle is not None:
			self.object.cancel_callback(self.update_handle)

	def on_enter(self, player: Player) -> None:
		if not self._enabled:
			return
		self.update_handle = self.object.call_later(0, self._update)

	def on_exit(self, player: Player) -> None:
		if self.update_handle is not None:
			self.object.cancel_callback(self.update_handle)

	def _update(self) -> None:
		# todo: move some targeting logic to TacArc
		self.target = None
		enemy_factions = server.db.factions.get(self.object.stats.faction, ())
		# todo: make distance skill-dependent
		nearest_dist = self.skill_range**2 # starting distance is maximum distance
		for obj in server.game_objects.values():
			if hasattr(obj, "stats") and obj.stats.faction in enemy_factions:
				dist = self.object.physics.position.sq_distance(obj.physics.position)
				if dist < nearest_dist:
					self.target = obj
					nearest_dist = dist
		if self.target is not None:
			pos_diff = self.target.physics.position - self.object.physics.position
			pos_diff.y = 0
			self.object.physics.rotation.update(Quaternion.look_rotation(pos_diff))
			self.object.physics.attr_changed("rotation")
			for skill_id in self.object.skill.skills:
				self.object.skill.cast_skill(skill_id, self.target)

			self.update_handle = self.object.call_later(UPDATE_INTERVAL, self._update)
