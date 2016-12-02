import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		teleport_obj = self.object._v_server.get_objects_in_group("Teleport")[0]
		self.object._v_server.send_game_message(player.char.teleport, ignore_y=False, pos=teleport_obj.physics.position, set_rotation=True, x=teleport_obj.physics.rotation.x, y=teleport_obj.physics.rotation.y, z=teleport_obj.physics.rotation.z, w=teleport_obj.physics.rotation.w, address=player.char.address)