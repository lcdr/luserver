from typing import List, Tuple

from pyraknet.bitstream import c_bit, c_float, c_int, c_uint, WriteStream
from ..game_object import CallbackID, Config, GameObject, Player
from ..world import server
from ..math.vector import Vector3
from .component import Component

# all of this is still quite uncertain

class Path:
	def __init__(self, behavior: int, waypoints: List[Tuple[Vector3, float, float]]):
		self.behavior = behavior
		self.waypoints = waypoints

class PathBehavior:
	Loop = 0
	Bounce = 1
	Once = 2

class MovementState:
	Moving = 2
	Stationary = 25
	Stopped = 28

class MovingPlatformComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.moving_platform = self
		self._flags["movement_state"] = "moving_platform_flag"
		self._flags["desired_waypoint_index"] = "moving_platform_flag"
		self._flags["unknown_bool"] = "moving_platform_flag"
		self._flags["in_reverse"] = "moving_platform_flag"
		self._flags["current_position"] = "moving_platform_flag"
		self._flags["current_waypoint_index"] = "moving_platform_flag"
		self._flags["next_waypoint_index"] = "moving_platform_flag"
		self.movement_state = MovementState.Stopped
		self.desired_waypoint_index = -1
		self.unknown_bool = False # possibly "stop on reaching desired waypoint"
		self.in_reverse = False
		self.current_position = Vector3()
		self.current_waypoint_index = 0
		self.next_waypoint_index = 1
		self.callbacks: List[CallbackID] = []
		self.no_autostart = False

		if "attached_path" in set_vars:
			self.path = Path(*server.world_data.paths[set_vars["attached_path"]])
			assert len(self.path.waypoints) > 1
			self.start_pathing()

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(self.moving_platform_flag))
		out.write(c_bit(False))
		if self.moving_platform_flag:
			out.write(c_bit(True))
			out.write(c_uint(4))
			# subcomponent 4 (mover?)
			out.write(c_bit(True))
			out.write(c_uint(self.movement_state))
			out.write(c_int(self.desired_waypoint_index))
			out.write(c_bit(self.unknown_bool))
			out.write(c_bit(self.in_reverse))
			out.write(c_float(0))
			out.write(self.current_position)
			out.write(c_uint(self.current_waypoint_index))
			out.write(c_uint(self.next_waypoint_index))
			out.write(c_float(0))
			out.write(c_uint(0))

			self.moving_platform_flag = False

	def on_rebuild_init(self) -> None:
		self.stop_pathing()

	def on_complete_rebuild(self, player: Player) -> None:
		if not self.no_autostart:
			self.start_pathing()

	def set_movement_state(self, state: int) -> None:
		self.movement_state = state

	def go_to_waypoint(self, index: int) -> None:
		self.desired_waypoint_index = index
		self.start_pathing()

	def start_pathing(self) -> None:
		self.unknown_bool = True

		self.movement_state = MovementState.Stationary
		position, speed, wait_time = self.path.waypoints[self.current_waypoint_index]
		self.current_position.update(position)

		self.callbacks.append(self.object.call_later(wait_time, self.set_movement_state, MovementState.Moving))
		target_position = self.path.waypoints[self.next_waypoint_index][0]
		travel_time = target_position.distance(self.current_position) / speed
		self.callbacks.append(self.object.call_later(wait_time+travel_time, self.continue_pathing))

	def continue_pathing(self) -> None:
		assert 0 <= self.current_waypoint_index < len(self.path.waypoints)
		assert 0 <= self.next_waypoint_index < len(self.path.waypoints)

		self.movement_state = MovementState.Stationary
		self.current_waypoint_index = self.next_waypoint_index
		position, speed, wait_time = self.path.waypoints[self.current_waypoint_index]
		self.current_position.update(position)

		if self.current_waypoint_index == len(self.path.waypoints)-1:
			assert not self.in_reverse
			if self.path.behavior == PathBehavior.Once:
				return
			if self.path.behavior == PathBehavior.Bounce:
				self.in_reverse = True
			elif self.path.behavior == PathBehavior.Loop:
				self.next_waypoint_index = 0
		elif self.current_waypoint_index == 0:
			assert self.path.behavior == PathBehavior.Bounce
			assert self.in_reverse
			self.in_reverse = False

		if not self.in_reverse:
			self.next_waypoint_index = self.current_waypoint_index + 1
			assert self.next_waypoint_index < len(self.path.waypoints)
		else:
			assert self.path.behavior == PathBehavior.Bounce
			self.next_waypoint_index = self.current_waypoint_index - 1
			assert self.next_waypoint_index >= 0

		if self.current_waypoint_index == self.desired_waypoint_index:
			self.object.handle("arrived_at_desired_waypoint", self.desired_waypoint_index, silent=True)
			self.stop_pathing()
			return

		self.callbacks.append(self.object.call_later(wait_time, self.set_movement_state, MovementState.Moving))
		target_position = self.path.waypoints[self.next_waypoint_index][0]
		travel_time = Vector3(target_position).distance(Vector3(position)) / speed
		self.callbacks.append(self.object.call_later(wait_time+travel_time, self.continue_pathing))

	def stop_pathing(self) -> None:
		for callback in self.callbacks:
			self.object.cancel_callback(callback)
		self.callbacks.clear()
		self.movement_state = MovementState.Stopped
		self.desired_waypoint_index = -1
		self.unknown_bool = False
