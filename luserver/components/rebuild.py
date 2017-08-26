import time

from ..bitstream import c_bit, c_float, c_int, c_uint
from ..game_object import GameObject
from ..messages import broadcast
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
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.rebuild = self
		self.complete_time = server.db.rebuild_component[comp_id][0]
		self.smash_time = server.db.rebuild_component[comp_id][1]
		self.reset_time = server.db.rebuild_component[comp_id][2]
		self.imagination_cost = server.db.rebuild_component[comp_id][3]
		self.callback_handles = []
		self.rebuild_start_time = 0
		self.last_progress = 0
		self._flags["rebuild_state"] = "rebuild_flag"
		self._flags["success"] = "rebuild_flag"
		self._flags["enabled"] = "rebuild_flag"
		self._rebuild_state = RebuildState.Open
		self.success = False
		self.enabled = True

		if "activity_id" in set_vars:
			self.activity_id = set_vars["activity_id"]
		else:
			self.activity_id = server.db.rebuild_component[comp_id][4]#self.object.lot
		self.completion_rewards = server.db.activity_rewards.get(self.activity_id, (None, None, None))

		if "rebuild_activator_position" in set_vars:
			self.rebuild_activator_position = set_vars["rebuild_activator_position"]
		else:
			self.rebuild_activator_position = Vector3(self.object.physics.position)

	def on_startup(self):
		server.spawn_object(ACTIVATOR_LOT, {"parent": self.object, "position": self.rebuild_activator_position})
		if hasattr(self.object, "ai"):
			self.object.ai.disable()
		if hasattr(self.object, "moving_platform"):
			self.object.moving_platform.stop_pathing()

	@property
	def rebuild_state(self):
		return self._rebuild_state

	@rebuild_state.setter
	def rebuild_state(self, value):
		player = server.get_object(list(self.activity_values)[0])
		self.rebuild_notify_state(self.rebuild_state, value, player)
		self._rebuild_state = value

	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		out.write(c_bit(self.rebuild_flag or is_creation))
		if self.rebuild_flag or is_creation:
			out.write(c_uint(self.rebuild_state))
			out.write(c_bit(self.success))
			out.write(c_bit(self.enabled))
			if self.rebuild_state == RebuildState.Building:
				out.write(c_float(time.time() - self.rebuild_start_time + self.last_progress))
			else:
				out.write(c_float(self.last_progress))
			out.write(c_float(0))
			if is_creation:
				out.write(c_bit(False))
				out.write(c_float(self.rebuild_activator_position.x))
				out.write(c_float(self.rebuild_activator_position.y))
				out.write(c_float(self.rebuild_activator_position.z))
				out.write(c_bit(True))
			self.rebuild_flag = False

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		if self.rebuild_state not in (RebuildState.Open, RebuildState.Incomplete):
			return
		for handle in self.callback_handles:
			self.object.cancel_callback(handle)
		self.callback_handles.clear()
		self.add_player(player)
		self.rebuild_state = RebuildState.Building
		player.char.rebuilding = 1
		self.enable_rebuild(enable=self.enabled, fail=False, success=self.success, duration=0, user=player)
		self.rebuild_start_time = time.time()
		drain_interval = self.complete_time/self.imagination_cost
		remaining_cost = int((self.complete_time - self.last_progress) // drain_interval)
		for i in range(remaining_cost):
			self.callback_handles.append(self.object.call_later(self.last_progress%drain_interval + drain_interval*i, self.drain_imagination, player))
		for handler in self.object.handlers("complete_rebuild"):
			self.callback_handles.append(self.object.call_later(self.complete_time-self.last_progress, handler, player))
		return True

	def drain_imagination(self, player):
		if player.stats.imagination == 0:
			self.rebuild_cancel(early_release=False, user_id=player.object_id)
		player.stats.imagination -= 1

	def complete_rebuild(self, player):
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

		player.char.update_mission_task(TaskType.QuickBuild, self.activity_id)

		# drop rewards
		self.object.physics.drop_rewards(*self.completion_rewards, player)

		if hasattr(self.object, "ai"):
			self.object.ai.enable()
		if hasattr(self.object, "moving_platform"):
			self.object.moving_platform.start_pathing()

	def smash_rebuild(self):
		self.object.stats.die(death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer=None)
		server.replica_manager.destruct(self.object)

	def rebuild_cancel(self, early_release:bool=None, user:GameObject=None):
		if self.rebuild_state == RebuildState.Building:
			for handle in self.callback_handles:
				self.object.cancel_callback(handle)
			self.callback_handles.clear()
			self.last_progress += time.time() - self.rebuild_start_time
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
	def enable_rebuild(self, enable:bool=None, fail:bool=None, success:bool=None, fail_reason:c_uint=FailReason.NotGiven, duration:float=None, user:GameObject=None):
		pass

	@broadcast
	def rebuild_notify_state(self, prev_state:c_int=None, state:c_int=None, player:GameObject=None):
		pass
