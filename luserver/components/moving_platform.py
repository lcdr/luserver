import asyncio
import itertools

from ..bitstream import c_bit, c_float, c_int, c_uint
from ..math.vector import Vector3
from .component import Component

class MovingPlatformComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.moving_platform = self
		self._flags["moving_platform_unknown"] = "moving_platform_flag"
		self._flags["target_position"] = "moving_platform_flag"
		self.target_position = Vector3()
		if "attached_path" in set_vars:
			self.attached_path = set_vars["attached_path"]
			self.moving_platform_unknown = 2
			self.current_waypoint_index = 0
			self.next_waypoint_index = 1
			self.waypoint_cycler = itertools.cycle(enumerate(self.object._v_server.world_data.paths[self.attached_path]))
			self.update_waypoint()

	def serialize(self, out, is_creation):
		out.write(c_bit(self.moving_platform_flag))
		out.write(c_bit(False))
		if self.moving_platform_flag:
			out.write(c_bit(True))
			out.write(c_uint(4))
			# subcomponent 4 (mover?)
			out.write(c_bit(True))
			out.write(c_uint(self.moving_platform_unknown))
			out.write(c_int(-1))
			out.write(c_bit(False))
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
		asyncio.get_event_loop().call_later(speed, self.update_moving_platform_unknown) # i have no idea what the right time interval is
		asyncio.get_event_loop().call_later(speed+wait_time, self.update_waypoint) # i have no idea what the right time interval is

	def update_moving_platform_unknown(self):
		if self.moving_platform_unknown == 2:
			self.moving_platform_unknown = 25
		else:
			self.moving_platform_unknown = 2
