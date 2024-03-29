import time
from typing import List, Optional

from bitstream import c_bit, c_float, c_uint, WriteStream
from ..game_object import broadcast, CallbackID, Config, EB, EF, EI, EO, EP, GameObject, OBJ_NONE, Player, StatsObject
from ..game_object import c_int as c_int_
from ..game_object import c_uint as c_uint_
from ..world import server
from ..math.vector import Vector3
from .char import TerminateType
from .mission import TaskType
from .scripted_activity import ScriptedActivityComponent

class RebuildState:
	Open = 0
	Completed = 2
	Resetting = 4
	Building = 5
	Incomplete = 6

class FailReason:
	NotGiven = 0
	OutOfImagination = 1
	CanceledEarly = 2
	BuildEnded = 3

ACTIVATOR_LOT = 6604

class RebuildComponent(ScriptedActivityComponent):
	object: StatsObject

	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.rebuild = self
		db_entry = server.db.rebuild_component[comp_id]
		self.complete_time = set_vars.get("rebuild_complete_time", db_entry[0])
		self.smash_time = set_vars.get("rebuild_smash_time", db_entry[1])
		self.reset_time = db_entry[2]
		self.imagination_cost = db_entry[3]
		self.callback_handles: List[CallbackID] = []
		self.rebuild_start_time: float = 0
		self.last_progress: float = 0
		self._flags["_rebuild_state"] = "_rebuild_flag"
		self._flags["success"] = "_rebuild_flag"
		self._flags["enabled"] = "_rebuild_flag"
		self._rebuild_state = RebuildState.Open
		self.success = False
		self.enabled = True
		self.activity_id = set_vars.get("activity_id", db_entry[4])
		if self.activity_id in server.db.activity_rewards:
			self.completion_rewards = server.db.activity_rewards[self.activity_id][0][1]
		else:
			self.completion_rewards = None, None, None

		if "rebuild_activator_position" in set_vars:
			self.rebuild_activator_position = set_vars["rebuild_activator_position"]
		else:
			self.rebuild_activator_position = Vector3(self.object.physics.position)

	def on_startup(self) -> None:
		server.spawn_object(ACTIVATOR_LOT, {"parent": self.object, "position": self.rebuild_activator_position})
		self.object.handle("rebuild_init", silent=True)

	@property
	def rebuild_state(self) -> int:
		return self._rebuild_state

	@rebuild_state.setter
	def rebuild_state(self, value: int) -> None:
		player = server.get_object(list(self.activity_values)[0])
		self.rebuild_notify_state(self.rebuild_state, value, player)
		self._rebuild_state = value

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		super().serialize(out, is_creation)
		if self.flag("_rebuild_flag", out, is_creation):
			out.write(c_uint(self.rebuild_state))
			out.write(c_bit(self.success))
			out.write(c_bit(self.enabled))
			if self.rebuild_state == RebuildState.Building:
				out.write(c_float(time.perf_counter() - self.rebuild_start_time + self.last_progress))
			else:
				out.write(c_float(self.last_progress))
			out.write(c_float(0))
			if is_creation:
				out.write(c_bit(False))
				out.write(self.rebuild_activator_position)
				out.write(c_bit(True))

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> bool:
		assert multi_interact_id is None
		if self.rebuild_state not in (RebuildState.Open, RebuildState.Incomplete):
			return False
		for handle in self.callback_handles:
			self.object.cancel_callback(handle)
		self.callback_handles.clear()
		self.add_player(player)
		self.rebuild_state = RebuildState.Building
		player.char.rebuilding = 1
		self.enable_rebuild(enable=self.enabled, fail=False, success=self.success, duration=0, user=player)
		self.rebuild_start_time = time.perf_counter()
		drain_interval = self.complete_time/self.imagination_cost
		remaining_cost = int((self.complete_time - self.last_progress) // drain_interval)
		for i in range(remaining_cost):
			self.callback_handles.append(self.object.call_later(self.last_progress % drain_interval + drain_interval * i, self._drain_imagination, player))
		for handler in self.object.handlers("complete_rebuild"):
			self.callback_handles.append(self.object.call_later(self.complete_time-self.last_progress, handler, player))
		return True

	def _drain_imagination(self, player: Player) -> None:
		if player.stats.imagination == 0:
			self.on_rebuild_cancel(early_release=False, user=player)
		player.stats.imagination -= 1

	def on_complete_rebuild(self, player: Player) -> None:
		self.rebuild_state = RebuildState.Completed
		self.success = True
		self.enabled = False
		player.char.rebuilding = 0
		self.enable_rebuild(enable=self.enabled, fail=False, success=self.success, duration=0, user=player)
		self.object.render.play_f_x_effect(name=b"BrickFadeUpVisCompleteEffect", effect_type="create", effect_id=507)
		player.render.play_animation("rebuild-celebrate")

		for child_id in self.object.children:
			child = server.game_objects[child_id]
			if child.lot == ACTIVATOR_LOT:
				server.replica_manager.destruct(child)
				break
		self.callback_handles.append(self.object.call_later(self.smash_time, self.smash_rebuild))

		player.char.mission.update_mission_task(TaskType.QuickBuild, self.activity_id)

		# drop rewards
		self.object.physics.drop_rewards(*self.completion_rewards, player)

	def smash_rebuild(self) -> None:
		self.object.stats.die(death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer=OBJ_NONE)
		server.replica_manager.destruct(self.object)

	def on_rebuild_cancel(self, early_release:bool=EB, user:Player=EP) -> None:
		if self.rebuild_state == RebuildState.Building:
			for handle in self.callback_handles:
				self.object.cancel_callback(handle)
			self.callback_handles.clear()
			self.last_progress += time.perf_counter() - self.rebuild_start_time
			self.rebuild_state = RebuildState.Incomplete
			self.remove_player(user)
			user.char.rebuilding = 0
			if early_release:
				fail_reason = FailReason.CanceledEarly
			else:
				fail_reason = FailReason.OutOfImagination
			self.enable_rebuild(enable=False, fail=True, success=self.success, fail_reason=fail_reason, duration=self.last_progress, user=user)
			user.char.terminate_interaction(terminator=self.object, type=TerminateType.FromInteraction)
			self.callback_handles.append(self.object.call_later(self.reset_time, self.smash_rebuild))

	@broadcast
	def enable_rebuild(self, enable:bool=EB, fail:bool=EB, success:bool=EB, fail_reason:c_uint_=FailReason.NotGiven, duration:float=EF, user:GameObject=EO) -> None:
		pass

	@broadcast
	def rebuild_notify_state(self, prev_state:c_int_=EI, state:c_int_=EI, player:GameObject=EO) -> None:
		pass
