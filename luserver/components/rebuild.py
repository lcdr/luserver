import asyncio
import time

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..math.vector import Vector3
from .char import TerminateType
from .mission import MissionState, TaskType
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
	def __init__(self, comp_id):
		super().__init__(comp_id)
		self.complete_time = self._v_server.db.rebuild_component[comp_id][0]
		self.smash_time = self._v_server.db.rebuild_component[comp_id][1]
		self.reset_time = self._v_server.db.rebuild_component[comp_id][2]
		self.imagination_cost = self._v_server.db.rebuild_component[comp_id][3]
		self.callback_handles = []
		self.rebuild_start_time = 0
		self.last_progress = 0
		self._flags["rebuild_state"] = "rebuild_flag"
		self._flags["success"] = "rebuild_flag"
		self._flags["enabled"] = "rebuild_flag"
		self._rebuild_state = RebuildState.Open
		self.success = False
		self.enabled = True

		if not hasattr(self, "rebuild_activator_position"):
			self.rebuild_activator_position = Vector3(self.position)

	@property
	def rebuild_state(self):
		return self._rebuild_state

	@rebuild_state.setter
	def rebuild_state(self, value):
		player = self._v_server.get_object(self.players[0])
		self._v_server.send_game_message(self.rebuild_notify_state, self.rebuild_state, value, player=player.object_id, address=player.address)
		self._rebuild_state = value

	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		out.write(c_bit(self.rebuild_flag or is_creation))
		if self.rebuild_flag or is_creation:
			out.write(c_uint(self.rebuild_state))
			out.write(c_bit(self.success))
			out.write(c_bit(self.enabled))
			out.write(c_float(time.time() - self.rebuild_start_time))
			out.write(c_uint(0))
			if is_creation:
				out.write(c_bit(False))
				out.write(c_float(self.rebuild_activator_position.x))
				out.write(c_float(self.rebuild_activator_position.y))
				out.write(c_float(self.rebuild_activator_position.z))
				out.write(c_bit(True))
			self.rebuild_flag = False

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		assert self.rebuild_state in (RebuildState.Open, RebuildState.Incomplete)
		for handle in self.callback_handles:
			handle.cancel()
		self.callback_handles.clear()
		self.players.append(player.object_id)
		self.activity_flag = True
		self.rebuild_state = RebuildState.Building
		player.rebuilding = 1
		self._v_server.send_game_message(self.enable_rebuild, enable=self.enabled, fail=False, success=self.success, duration=0, user=player.object_id, address=player.address)
		self.rebuild_start_time = time.time()
		drain_interval = self.complete_time/self.imagination_cost
		remaining_cost = int((self.complete_time - self.last_progress) // drain_interval)
		for i in range(remaining_cost):
			self.callback_handles.append(asyncio.get_event_loop().call_later(self.last_progress%drain_interval + drain_interval*i, self.drain_imagination, player))
		self.callback_handles.append(asyncio.get_event_loop().call_later(self.complete_time-self.last_progress, self.complete_rebuild, player))
		return True

	def drain_imagination(self, player):
		player.imagination -= 1
		if player.imagination == 0:
			self.rebuild_cancel(None, early_release=False, user_id=player.object_id)

	def complete_rebuild(self, player):
		self.rebuild_state = RebuildState.Completed
		self.success = True
		self.enabled = False
		player.rebuilding = 0
		self._v_server.send_game_message(self.enable_rebuild, enable=self.enabled, fail=False, success=self.success, duration=0, user=player.object_id, address=player.address)
		self._v_server.send_game_message(self.play_f_x_effect, name="BrickFadeUpVisCompleteEffect", effect_type="create", effect_id=507, address=player.address)
		self._v_server.send_game_message(player.play_animation, animation_id="rebuild-celebrate", play_immediate=False, address=player.address)

		assert len(self.children) == 1
		self._v_server.destruct(self._v_server.game_objects[self.children[0]])
		asyncio.get_event_loop().call_later(self.smash_time, self.smash_rebuild)

		# update missions that have completing this rebuild as requirement
		for mission in player.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.QuickBuild and task.target == self.lot:
						mission.increment_task(task, player)

	def smash_rebuild(self):
		self._v_server.send_game_message(self.die, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=0, broadcast=True)
		self._v_server.destruct(self)

	def rebuild_cancel(self, address, early_release:c_bit=None, user_id:c_int64=None):
		player = self._v_server.get_object(user_id)
		if self.rebuild_state == RebuildState.Building:
			for handle in self.callback_handles:
				handle.cancel()
			self.callback_handles.clear()
			self.last_progress += time.time() - self.rebuild_start_time
			self.rebuild_state = RebuildState.Incomplete
			self.players.remove(user_id)
			self.activity_flag = True
			player.rebuilding = 0
			if early_release:
				fail_reason = FailReason.CanceledEarly
			else:
				fail_reason = FailReason.OutOfImagination
			self._v_server.send_game_message(self.enable_rebuild, enable=False, fail=True, success=self.success, fail_reason=fail_reason, duration=self.last_progress, user=player.object_id, address=player.address)
			self.callback_handles.append(asyncio.get_event_loop().call_later(self.reset_time, self.smash_rebuild))
		self._v_server.send_game_message(player.terminate_interaction, obj_id_terminator=self.object_id, type=TerminateType.FromInteraction, address=player.address)

	def enable_rebuild(self, address, enable:c_bit=None, fail:c_bit=None, success:c_bit=None, fail_reason:c_uint=FailReason.NotGiven, duration:c_float=None, user:c_int64=None):
		pass

	def rebuild_notify_state(self, address, prev_state:c_int=None, state:c_int=None, player:c_int64=None):
		pass