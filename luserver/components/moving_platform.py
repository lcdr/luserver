import itertools

from ..bitstream import c_bit, c_float, c_int, c_uint
from ..math.vector import Vector3
from .component import Component

# all of this is still quite uncertain

class MovementState:
	Moving = 2
	Stationary = 25
	Stopped = 28

class MovingPlatformComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.moving_platform = self
		self._flags["movement_state"] = "moving_platform_flag"
		self._flags["target_position"] = "moving_platform_flag"
		self.target_position = Vector3()
		if "attached_path" in set_vars:
			self.path = self.object._v_server.world_data.paths[set_vars["attached_path"]]
			self.movement_state = MovementState.Stopped
			self.desired_waypoint_index = -1
			self.unknown_bool = False # possibly "stop on reaching desired waypoint"
			self.current_waypoint_index = 0
			self.next_waypoint_index = 1
			self.waypoint_cycler = itertools.cycle(enumerate(self.path))
			#self.update_waypoint()

	def serialize(self, out, is_creation):
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
			out.write(c_bit(self.current_waypoint_index > self.next_waypoint_index))
			out.write(c_float(0))
			out.write(c_float(self.target_position.x))
			out.write(c_float(self.target_position.y))
			out.write(c_float(self.target_position.z))
			out.write(c_uint(self.current_waypoint_index))
			out.write(c_uint(self.next_waypoint_index))
			out.write(c_float(0))
			out.write(c_uint(0))

			self.moving_platform_flag = False

	def update_waypoint(self):
		index, current_waypoint = next(self.waypoint_cycler)
		position, speed, wait_time = current_waypoint
		self.target_position.update(*position)
		self.current_waypoint_index = self.next_waypoint_index
		self.next_waypoint_index = index
		#self.object.call_later(speed, self.update_movement_state) # i have no idea what the right time interval is
		#self.update_handle = self.object.call_later(speed+wait_time, self.update_waypoint) # i have no idea what the right time interval is

	def set_movement_state(self, state):
		self.movement_state = state

	def go_to_waypoint(self, index):
		# todo: should probably transition from current index over other indices to target index
		self.movement_state = MovementState.Stationary
		self.desired_waypoint_index = index
		self.unknown_bool = True
		self.current_waypoint_index = (index-1) % len(self.path)
		position, speed, wait_time = self.path[self.current_waypoint_index]
		self.target_position.update(*position)
		self.next_waypoint_index = (self.current_waypoint_index+1) % len(self.path)
		self.object.call_later(wait_time, self.set_movement_state, MovementState.Moving)
		if self.next_waypoint_index == index:
			target_position = self.path[self.next_waypoint_index][0]
			travel_time = Vector3(target_position).distance(Vector3(position)) / speed
			self.object.call_later(wait_time+travel_time, lambda: self.object.handle("arrived_at_desired_waypoint", index, silent=True))

	def stop_pathing(self):
		self.movement_state = MovementState.Stopped
		self.desired_waypoint_index = -1
		self.unknown_bool = False
