import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		for obj in self.object._v_server.world_data.objects.values():
			if obj.lot == 4945:
				print(obj.groups)
			#if obj.lot == 4945 and self.script_vars["teleport_respawn_point_name"] in obj.groups: # respawn point lot
				self.object._v_server.send_game_message(player.char.teleport, ignore_y=False, pos=obj.position, set_rotation=True, x=obj.rotation.x, y=obj.rotation.y, z=obj.rotation.z, w=obj.rotation.w, address=player.char.address)
				break
