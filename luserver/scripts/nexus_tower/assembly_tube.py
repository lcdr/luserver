import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		for obj in self.object._v_server.world_data.objects.values():
			if obj.lot == 4945 and self.script_vars["teleport_respawn_point_name"] in obj.groups: # respawn point lot
				self.object._v_server.send_game_message(player.char.teleport, ignore_y=False, pos=obj.physics.position, set_rotation=True, x=obj.physics.rotation.x, y=obj.physics.rotation.y, z=obj.physics.rotation.z, w=obj.physics.rotation.w, address=player.char.address)
				break