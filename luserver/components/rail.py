from .component import Component

class RailActivatorComponent(Component):
	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object._v_server.send_game_message(player.char.start_rail_movement, path_go_forward=self.rail_path_start == 0, loop_sound="", path_name=self.rail_path, path_start=self.rail_path_start, rail_activator_component_id=6, rail_activator_obj_id=self.object.object_id, start_sound="", stop_sound="", address=player.char.address)
		self.object._v_server.send_game_message(player.char.set_rail_movement, path_go_forward=self.rail_path_start == 0, path_name=self.rail_path, path_start=self.rail_path_start, address=player.char.address)

		# possibly belongs in a script, newer scripts were removed so i can't tell
		player.char.set_flag(None, True, 2020)
