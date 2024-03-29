from typing import cast

import luserver.components.script as script
from luserver.game_object import c_int64, GameObject, OBJ_NONE, Player, RenderObject, single
from luserver.ldf import LDFDataType
from luserver.world import server
from luserver.components.mission import MissionState, TaskType

FLAG_DEFEATED_SPIDER = 71

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.tutorial = None

	def player_ready(self, player: Player) -> None:
		if not player.char.get_flag(FLAG_DEFEATED_SPIDER):
			self.start_maelstrom()
		else:
			server.spawners["FXObject"].spawner.destroy()

		# todo: implement distinction between instance and claim property (different launcher)
		for spawner in ("Launcher", "Mailbox"):
			server.spawners[spawner].spawner.activate()

		if 320 not in player.char.mission.missions:
			server.spawners["PropertyGuard"].spawner.activate()

	player_ready = single(player_ready)
	on_player_ready = player_ready

	def start_maelstrom(self):
		for spawner in ("SpiderBoss", "SpiderEggs", "Spider_Scream"):
			server.spawners[spawner].spawner.activate()

		server.spawners["Rocks"].spawner.activate()

		for spawner in ("BirdFX", "SunBeam"):
			server.spawners[spawner].spawner.destroy()

		self.set_network_var("unclaimed", LDFDataType.BOOLEAN, True)

		fx = cast(RenderObject, server.get_objects_in_group("FXObject")[0])
		fx.render.play_f_x_effect(name=b"TornadoDebris", effect_type="debrisOn")
		fx.render.play_f_x_effect(name=b"TornadoVortex", effect_type="VortexOn")
		fx.render.play_f_x_effect(name=b"silhouette", effect_type="onSilhouette")

		self.notify_client_object(name="maelstromSkyOn", param1=0, param2=0, param_str=b"", param_obj=OBJ_NONE)

	def on_spider_defeated(self):
		player = cast(Player, [obj for obj in server.game_objects.values() if obj.lot == 1][0])
		if player.char.get_flag(FLAG_DEFEATED_SPIDER):
			return
		server.spawners["SpiderBoss"].spawner.deactivate()
		for spawner in ("AggroVol", "Instancer", "Land_Target", "Rocks", "RFS_Targets", "SpiderEggs", "SpiderRocket_Bot", "SpiderRocket_Mid", "SpiderRocket_Top", "TeleVol"):
			server.spawners[spawner].spawner.destroy()
		for i in range(5):
			server.spawners["ROF_Targets_0"+str(i)].spawner.destroy()
		for i in range(1, 9):
			server.spawners["Zone"+str(i)+"Vol"].spawner.destroy()
		self.notify_client_object(name="PlayCinematic", param1=0, param2=0, param_str=b"DestroyMaelstrom", param_obj=OBJ_NONE)
		player.char.set_flag(True, FLAG_DEFEATED_SPIDER)
		self.object.call_later(0.5, self.tornado_off)

	def tornado_off(self):
		fx = cast(RenderObject, server.get_objects_in_group("FXObject")[0])
		fx.render.stop_f_x_effect(name=b"TornadoDebris")
		fx.render.stop_f_x_effect(name=b"TornadoVortex")
		fx.render.stop_f_x_effect(name=b"silhouette")
		self.object.call_later(2, self.show_clear_effects)

	def show_clear_effects(self):
		fx = cast(RenderObject, server.get_objects_in_group("FXObject")[0])
		fx.render.play_f_x_effect(name=b"beam", effect_type="beamOn")
		self.object.call_later(1.5, self.turn_sky_off)
		self.object.call_later(7, self.show_vendor)
		self.object.call_later(8, self.kill_fx_object)

	def turn_sky_off(self):
		self.notify_client_object(name="SkyOff", param1=0, param2=0, param_str=b"", param_obj=OBJ_NONE)

	def show_vendor(self):
		self.notify_client_object(name="vendorOn", param1=0, param2=0, param_str=b"", param_obj=OBJ_NONE)

	def kill_fx_object(self):
		fx = cast(RenderObject, server.get_objects_in_group("FXObject")[0])
		fx.render.stop_f_x_effect(name=b"beam")
		server.spawners["FXObject"].spawner.destroy()

	def on_property_rented(self, player):
		self.notify_client_object(name="PlayCinematic", param1=0, param2=0, param_str=b"ShowProperty", param_obj=OBJ_NONE)
		player.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=951)
		self.object.call_later(2, self.bounds_on)

	def bounds_on(self):
		self.notify_client_object(name="boundsAnim", param1=0, param2=0, param_str=b"", param_obj=OBJ_NONE)


	def on_build_mode(self, start):
		if start:
			self.set_network_var("PlayerAction", LDFDataType.STRING, "Enter")
		else:
			self.set_network_var("PlayerAction", LDFDataType.STRING, "Exit")

	def on_model_placed(self, player):
		if not player.char.get_flag(101):
			player.char.set_flag(True, 101)
			if 871 in player.char.mission.missions and player.char.mission.missions[871].state == MissionState.Active:
				self.set_network_var("Tooltip", LDFDataType.STRING, "AnotherModel")

		elif not player.char.get_flag(102):
			player.char.set_flag(True, 102)
			if 871 in player.char.mission.missions and player.char.mission.missions[871].state == MissionState.Active:
				self.set_network_var("Tooltip", LDFDataType.STRING, "TwoMoreModels")

		elif not player.char.get_flag(103):
			player.char.set_flag(True, 103)

		elif not player.char.get_flag(104):
			player.char.set_flag(True, 104)
			self.set_network_var("Tooltip", LDFDataType.STRING, "TwoMoreModelsOff")

		elif self.tutorial == "place_model":
			self.tutorial = None
			self.set_network_var("Tooltip", LDFDataType.STRING, "PutAway")

	def on_model_picked_up(self, player):
		if not player.char.get_flag(109):
			player.char.set_flag(True, 109)
			if 891 in player.char.mission.missions and player.char.mission.missions[891].state == MissionState.Active and not player.char.get_flag(110):
				self.set_network_var("Tooltip", LDFDataType.STRING, "Rotate")

	def on_model_put_away(self, player):
		player.char.set_flag(True, 111)

	def on_zone_property_model_rotated(self, player:Player=OBJ_NONE, property_id:c_int64=0):
		if not player.char.get_flag(110):
			player.char.set_flag(True, 110)
			if 891 in player.char.mission.missions and player.char.mission.missions[891].state == MissionState.Active:
				self.set_network_var("Tooltip", LDFDataType.STRING, "PlaceModel")
				self.tutorial = "place_model"

	def on_zone_property_model_removed_while_equipped(self, player:Player=OBJ_NONE, property_id:c_int64=0):
		self.on_model_put_away(player)

	def on_zone_property_model_equipped(self, player:GameObject=OBJ_NONE, property_id:c_int64=0):
		self.set_network_var("PlayerAction", LDFDataType.STRING, "ModelEquipped")
