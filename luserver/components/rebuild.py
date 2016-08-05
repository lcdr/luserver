import asyncio

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..math.vector import Vector3
from .mission import MissionState, TaskType
from .scripted_activity import ScriptedActivityComponent

class RebuildState:
	Open = 0
	Completed = 2
	Resetting = 4
	Building = 5

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

		self._flags["rebuild_state"] = "rebuild_flag"
		self._flags["success"] = "rebuild_flag"
		self._flags["enabled"] = "rebuild_flag"
		self._flags["rebuild_duration"] = "rebuild_flag"
		self.rebuild_state = RebuildState.Open
		self.success = False
		self.enabled = True
		self.rebuild_duration = 0

		if not hasattr(self, "rebuild_activator_position"):
			self.rebuild_activator_position = Vector3(self.position)

	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		out.write(c_bit(self.rebuild_flag or is_creation))
		if self.rebuild_flag or is_creation:
			out.write(c_uint(self.rebuild_state))
			out.write(c_bit(self.success))
			out.write(c_bit(self.enabled))
			out.write(c_float(self.rebuild_duration))
			out.write(c_uint(0))
			if is_creation:
				out.write(c_bit(False))
				out.write(c_float(self.rebuild_activator_position.x))
				out.write(c_float(self.rebuild_activator_position.y))
				out.write(c_float(self.rebuild_activator_position.z))
				out.write(c_bit(True))
			self.rebuild_flag = False

	def on_use(self, player, multi_interact_id):
		if self.rebuild_state == RebuildState.Open:
			assert multi_interact_id is None
			prev_state = self.rebuild_state
			self.rebuild_state = RebuildState.Building
			self.players.append(player.object_id)
			self.activity_flag = True
			player.rebuilding = 1
			self._v_server.send_game_message(self.rebuild_notify_state, prev_state, self.rebuild_state, player=player.object_id, address=player.address)
			self._v_server.send_game_message(self.enable_rebuild, enable=True, fail=False, success=False, duration=0, user=player.object_id, address=player.address)


			asyncio.get_event_loop().call_later(self.complete_time, self.complete_rebuild, player)
			return True

	def complete_rebuild(self, player):
		prev_state = self.rebuild_state
		self.rebuild_state = RebuildState.Completed
		self.success = True
		self.enabled = False
		self.rebuild_duration = self.complete_time
		player.rebuilding = 0
		self._v_server.send_game_message(self.rebuild_notify_state, prev_state, self.rebuild_state, player=player.object_id, address=player.address)
		self._v_server.send_game_message(self.enable_rebuild, enable=False, fail=False, success=True, duration=0, user=player.object_id, address=player.address)
		self._v_server.send_game_message(player.play_animation, animation_id="rebuild-celebrate", play_immediate=False, address=player.address)

		assert len(self.children) == 1
		self._v_server.destruct(self._v_server.game_objects[self.children[0]])
		asyncio.get_event_loop().call_later(self.smash_time, self.smash_rebuild)

		# update missions that have completing this rebuild as requirement
		for mission in player.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.QuickBuild and task.target == self.lot:
						mission.increment_task(task, self._v_server, player)

	def smash_rebuild(self):
		self._v_server.send_game_message(self.die, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=0, broadcast=True)
		self._v_server.destruct(self)

	def rebuild_cancel(self, address, early_release:c_bit=None, user_id:c_int64=None):
		pass#self.rebuild_state = RebuildState.Open
		#self.players.remove(user_id)
		#self.activity_flag = True

	def enable_rebuild(self, address, enable:c_bit=None, fail:c_bit=None, success:c_bit=None, fail_reason:c_uint=FailReason.NotGiven, duration:c_float=None, user:c_int64=None):
		pass

	def rebuild_notify_state(self, address, prev_state:c_int=None, state:c_int=None, player:c_int64=None):
		pass