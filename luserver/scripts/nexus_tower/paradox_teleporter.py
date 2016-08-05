import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_collision(self, player):
		for obj in self._v_server.world_data.objects.values():
			if obj.lot == 4945 and self.script_vars["teleport_respawn_point_name"] in obj.groups: # respawn point lot
				self._v_server.send_game_message(player.teleport, ignore_y=False, pos=obj.position, set_rotation=True, x=obj.rotation.x, y=obj.rotation.y, z=obj.rotation.z, w=obj.rotation.w, address=player.address)
				break
