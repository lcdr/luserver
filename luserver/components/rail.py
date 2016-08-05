
class RailActivatorComponent:
	def __init__(self, comp_id):
		pass

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self._v_server.send_game_message(player.start_rail_movement, path_go_forward=self.rail_path_start == 0, loop_sound="", path_name=self.rail_path, path_start=self.rail_path_start, rail_activator_component_id=6, rail_activator_obj_id=self.object_id, start_sound="", stop_sound="", address=player.address)
		self._v_server.send_game_message(player.set_rail_movement, path_go_forward=self.rail_path_start == 0, path_name=self.rail_path, path_start=self.rail_path_start, address=player.address)

		# possibly belongs in a script, newer scripts were removed so i can't tell
		player.set_flag(None, True, 2020)
