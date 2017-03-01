import luserver.components.script as script

SOUND_NAME = "{9a24f1fa-3177-4745-a2df-fbd996d6e1e3}"

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.moving_platform.stop_pathing()
		self.players_in_radius = 0
		self.object.physics.proximity_radius(40)

	def on_enter(self, player):
		if self.players_in_radius == 0:
			self.object.moving_platform.go_to_waypoint(0)
			self.object.render.play_n_d_audio_emitter(event_guid=SOUND_NAME, meta_event_name="")
		self.players_in_radius += 1

	def on_exit(self, player):
		self.players_in_radius -= 1
		if self.players_in_radius == 0:
			self.object.moving_platform.go_to_waypoint(1)
			self.object.render.play_n_d_audio_emitter(event_guid=SOUND_NAME, meta_event_name="")

	def arrived_at_desired_waypoint(self, index):
		if index == 1:
			self.object.render.play_f_x_effect(name="busDust", effect_type="create")
