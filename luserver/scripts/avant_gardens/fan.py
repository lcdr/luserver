import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.enable_fx(True)

	def on_destruction(self):
		self.enable_fx(False)

	def fire_event(self, event):
		if event == "turnOn":
			self.enable_fx(True)
		elif event == "turnOff":
			self.enable_fx(False)

	def enable_fx(self, enable=None):
		fx_obj = self.object._v_server.get_objects_in_group(self.object.groups[0]+"fx")[0]
		objs = self.object._v_server.get_objects_in_group(self.object.groups[0])
		for obj in objs:
			if obj.lot == 5958:
				if enable is None:
					enable = not obj.physics.physics_effect_active
				obj.physics.physics_effect_active = enable

		if enable:
			self.object.render.play_animation("fan-on", play_immediate=True)
			self.object.render.play_f_x_effect(name=b"fanOn",  effect_type="fanOn", effect_id=495)
			fx_obj.render.play_animation("idle", play_immediate=True)
		else:
			self.object.render.play_animation("fan-off", play_immediate=True)
			self.object.render.stop_f_x_effect(name=b"fanOn")
			fx_obj.render.play_animation("trigger", play_immediate=True)
