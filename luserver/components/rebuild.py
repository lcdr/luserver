import time

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..messages import broadcast
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

class RebuildComponent(ScriptedActivityComponent):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.rebuild = self
		self.complete_time = self.object._v_server.db.rebuild_component[comp_id][0]
		self.smash_time = self.object._v_server.db.rebuild_component[comp_id][1]
		self.reset_time = self.object._v_server.db.rebuild_component[comp_id][2]
		self.imagination_cost = self.object._v_server.db.rebuild_component[comp_id][3]
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
			self.activity_id = self.object._v_server.db.rebuild_component[comp_id][4]#self.object.lot
		self.completion_rewards = self.object._v_server.db.activity_rewards.get(self.activity_id, (None, None, None))

		if "rebuild_activator_position" in set_vars:
			self.rebuild_activator_position = set_vars["rebuild_activator_position"]
		else:
			self.rebuild_activator_position = Vector3(self.object.physics.position)

	def on_startup(self):
		self.object._v_server.spawn_object(6604, {"parent": self.object, "position": self.rebuild_activator_position})
		if hasattr(self.object, "ai"):
			self.object.ai.disable()

	@property
	def rebuild_state(self):
		return self._rebuild_state

	@rebuild_state.setter
	def rebuild_state(self, value):
		player = self.object._v_server.get_object(list(self.activity_values)[0])
		self.rebuild_notify_state(self.rebuild_state, value, player_id=player.object_id)
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
		self.enable_rebuild(enable=self.enabled, fail=False, success=self.success, duration=0, user=player.object_id)
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
		self.enable_rebuild(enable=self.enabled, fail=False, success=self.success, duration=0, user=player.object_id)
		self.object.render.play_f_x_effect(name="BrickFadeUpVisCompleteEffect", effect_type="create", effect_id=507)
		player.render.play_animation(animation_id="rebuild-celebrate", play_immediate=False)

		assert len(self.object.children) == 1
		self.object._v_server.destruct(self.object._v_server.game_objects[self.object.children[0]])
		self.callback_handles.append(self.object.call_later(self.smash_time, self.smash_rebuild))

		player.char.update_mission_task(TaskType.QuickBuild, self.activity_id)

		# drop rewards
		self.object.physics.drop_rewards(*self.completion_rewards, player)

		# if this is a moving platform, set the waypoint
		if hasattr(self, "moving_platform"):
			self.moving_platform.update_waypoint()

		if hasattr(self.object, "ai"):
			self.object.ai.enable()

	def smash_rebuild(self):
		self.object.stats.die(death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=0)
		self.object._v_server.destruct(self.object)

	def rebuild_cancel(self, early_release:c_bit=None, user_id:c_int64=None):
		if self.rebuild_state == RebuildState.Building:
			for handle in self.callback_handles:
				self.object.cancel_callback(handle)
			self.callback_handles.clear()
			self.last_progress += time.time() - self.rebuild_start_time
			self.rebuild_state = RebuildState.Incomplete
			player = self.object._v_server.get_object(user_id)
			self.remove_player(player)
			player.char.rebuilding = 0
			if early_release:
				fail_reason = FailReason.CanceledEarly
			else:
				fail_reason = FailReason.OutOfImagination
			self.enable_rebuild(enable=False, fail=True, success=self.success, fail_reason=fail_reason, duration=self.last_progress, user=player.object_id)
			player.char.terminate_interaction(obj_id_terminator=self.object.object_id, type=TerminateType.FromInteraction)
			self.callback_handles.append(self.object.call_later(self.reset_time, self.smash_rebuild))

	@broadcast
	def enable_rebuild(self, enable:c_bit=None, fail:c_bit=None, success:c_bit=None, fail_reason:c_uint=FailReason.NotGiven, duration:c_float=None, user:c_int64=None):
		pass

	@broadcast
	def rebuild_notify_state(self, prev_state:c_int=None, state:c_int=None, player_id:c_int64=None):
		pass
