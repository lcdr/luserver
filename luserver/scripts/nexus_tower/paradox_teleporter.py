import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		for obj in self.object._v_server.world_data.objects.values():
			if obj.lot == 4945 and self.script_vars["teleport_respawn_point_name"] in obj.groups: # respawn point lot
				player.render.play_animation("teledeath", play_immediate=True, priority=4)
				self.object.call_later(0.5, self.teleport, player, obj)
				break

	def teleport(self, player, obj):
		player.char.play_cinematic(close_multi_interact=False, send_server_notify=False, lock_player=True, path_name=self.script_vars["cinematic"], start_time_advance=0)
		player.char.teleport(ignore_y=False, pos=obj.physics.position, set_rotation=True, x=obj.physics.rotation.x, y=obj.physics.rotation.y, z=obj.physics.rotation.z, w=obj.physics.rotation.w)
		player.render.play_animation("paradox-teleport-in", play_immediate=True, priority=4)
