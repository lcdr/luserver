import asyncio
import logging

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from ..bitstream import BitStream, c_bit, c_bool, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from ..messages import WorldClientMsg
from ..world import World
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from ..modules.social import FriendUpdateType
from .component import Component
from .inventory import InventoryType, LootType
from .pet import PetTamingNotify
from .mission import MissionProgress, MissionState, TaskType

log = logging.getLogger(__name__)

class TerminateType:
	Range = 0
	User = 1
	FromInteraction = 2

class BuildType:
	BuildNowhere = 0
	BuildInWorld = 1
	BuildOnProperty = 2

class DeleteReason:
	PickingModelUp = 0
	ReturningModelToInventory = 1
	BreakingModelApart = 2

class MatchRequestType:
	Join = 0
	Ready = 1

class MatchRequestValue:
	Leave = 0
	Ready = 1
	Join = 5


class MatchUpdateType:
	Time = 3

class CharacterComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.char = self
		# DB stuff

		self.address = None
		self._online = False
		self._world = 0, 0, 0
		self.currency = 0
		self.friends = PersistentList()
		self.mails = PersistentList()
		self.missions = PersistentList()
		# add achievements
		for mission_id, data in self.object._v_server.db.missions.items():
			is_mission = data[3] # if False, it's an achievement (internally works the same as missions, that's why the naming is weird)
			if not is_mission:
				self.missions.append(MissionProgress(mission_id, data))

		self.unlocked_emotes = PersistentList()

		self.clone_id = self.object._v_server.new_clone_id()

		for world in (World.BlockYard, World.AvantGrove, World.NimbusRock, World.NimbusIsle, World.ChanteyShanty, World.RavenBluff):
			self.object._v_server.db.properties[world.value][self.clone_id] = PersistentMapping()

		# Component stuff

		self._flags["vehicle_id"] = "vehicle_id_flag"
		self._flags["vehicle_id_flag"] = "vehicle_flag"
		self.vehicle_id = 0

		self._flags["level"] = "level_flag"
		self.level = 1

		self.flags = 0

		self.hair_color = 0
		self.hair_style = 0
		self.shirt_color = 0
		self.pants_color = 0
		self.eyebrow_style = 0
		self.eye_style = 0
		self.mouth_style = 0
		self.account_id = 0
		self.universe_score = 0
		self.is_FTP = False
		# statistics
		self.total_currency_collected = 0
		self.bricks_collected = 0
		self.smashables_smashed = 0
		self.quick_builds_completed = 0
		self.enemies_smashed = 0
		self.rockets_used = 0
		self.missions_completed = 0
		self.pets_tamed = 0
		self.imagination_power_ups_collected = 0
		self.life_power_ups_collected = 0
		self.armor_power_ups_collected = 0
		self.total_distance_traveled = 0
		self.times_smashed = 0
		self.total_damage_taken = 0
		self.total_damage_healed = 0
		self.total_armor_repaired = 0
		self.total_imagination_restored = 0
		self.total_imagination_used = 0
		self.total_distance_driven = 0
		self.total_time_airborne_in_a_race_car = 0
		self.racing_imagination_power_ups_collected = 0
		self.racing_imagination_crates_smashed = 0
		self.times_race_car_boost_activated = 0
		self.wrecks_in_a_race_car = 0
		self.racing_smashables_smashed = 0
		self.races_finished = 0
		self.first_place_race_finishes = 0

		self._flags["rebuilding"] = "rebuilding_flag"
		self.rebuilding = 0

	def serialize(self, out, is_creation):
		# First index
		out.write(c_bit(self.vehicle_flag))
		if self.vehicle_flag:
			out.write(c_bit(self.vehicle_id_flag))
			if self.vehicle_id_flag:
				out.write(c_int64(self.vehicle_id))
				self.vehicle_id_flag = False
			out.write(c_ubyte(1)) # unknown
			self.vehicle_flag = False

		# Second index
		out.write(c_bit(self.level_flag or is_creation))
		if self.level_flag or is_creation:
			out.write(c_uint(self.level))
			self.level_flag = False

		# Third index
		# This index is shared with other components, reflect that when we implement the other ones
		out.write(c_bit(False))

		# Fourth index
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_bit(False))

			out.write(c_uint(self.hair_color))
			out.write(c_uint(self.hair_style))
			out.write(bytes(4))
			out.write(c_uint(self.shirt_color))
			out.write(c_uint(self.pants_color))
			out.write(bytes(4))
			out.write(bytes(4))
			out.write(c_uint(self.eyebrow_style))
			out.write(c_uint(self.eye_style))
			out.write(c_uint(self.mouth_style))

			out.write(c_uint64(self.account_id))
			out.write(bytes(8))
			out.write(bytes(8))
			out.write(c_uint64(self.universe_score))
			out.write(c_bit(self.is_FTP))

			# Stats table values
			out.write(c_uint64(self.total_currency_collected))
			out.write(c_uint64(self.bricks_collected))
			out.write(c_uint64(self.smashables_smashed))
			out.write(c_uint64(self.quick_builds_completed))
			out.write(c_uint64(self.enemies_smashed))
			out.write(c_uint64(self.rockets_used))
			out.write(c_uint64(self.missions_completed))
			out.write(c_uint64(self.pets_tamed))
			out.write(c_uint64(self.imagination_power_ups_collected))
			out.write(c_uint64(self.life_power_ups_collected))
			out.write(c_uint64(self.armor_power_ups_collected))
			out.write(c_uint64(self.total_distance_traveled))
			out.write(c_uint64(self.times_smashed))
			out.write(c_uint64(self.total_damage_taken))
			out.write(c_uint64(self.total_damage_healed))
			out.write(c_uint64(self.total_armor_repaired))
			out.write(c_uint64(self.total_imagination_restored))
			out.write(c_uint64(self.total_imagination_used))
			out.write(c_uint64(self.total_distance_driven))
			out.write(c_uint64(self.total_time_airborne_in_a_race_car))
			out.write(c_uint64(self.racing_imagination_power_ups_collected))
			out.write(c_uint64(self.racing_imagination_crates_smashed))
			out.write(c_uint64(self.times_race_car_boost_activated))
			out.write(c_uint64(self.wrecks_in_a_race_car))
			out.write(c_uint64(self.racing_smashables_smashed))
			out.write(c_uint64(self.races_finished))
			out.write(c_uint64(self.first_place_race_finishes))
			out.write(c_bit(False))
			out.write(c_bit(False))

		out.write(c_bit(False))
		out.write(c_bit(self.rebuilding_flag))
		if self.rebuilding_flag:
			out.write(c_uint(self.rebuilding))
			self.rebuilding_flag = False
		out.write(c_bit(False))

	@property
	def online(self):
		return self._online

	@online.setter
	def online(self, value):
		self._online = value
		if value:
			self.send_friend_update_notify(FriendUpdateType.Login)
		else:
			self.send_friend_update_notify(FriendUpdateType.Logout)

	@property
	def world(self):
		return self._world

	@world.setter
	def world(self, value):
		self._world = value
		self.send_friend_update_notify(FriendUpdateType.WorldChange)

	def send_friend_update_notify(self, update_type):
		update_notify = BitStream()
		update_notify.write_header(WorldClientMsg.FriendUpdateNotify)
		update_notify.write(c_ubyte(update_type))
		update_notify.write(self.object.name, allocated_length=66)
		update_notify.write(c_ushort(self.world[0]))
		update_notify.write(c_ushort(self.world[1]))
		update_notify.write(c_uint(self.world[2]))
		update_notify.write(c_bool(False)) # is best friend
		update_notify.write(c_bool(False)) # is FTP

		for friend_ref in self.friends:
			self.object._v_server.send(update_notify, friend_ref().char.address)

	def on_destruction(self):
		if self.object.object_id in self.object._v_server.dropped_loot:
			del self.object._v_server.dropped_loot[self.object.object_id]
		self.vehicle_id = 0
		self.online = False
		self.check_for_leaks()

	def check_for_leaks(self):
		if self.object.inventory.temp_models:
			print("Temp Models not empty")
			print(self.object.inventory.temp_models)

	async def transfer_to_world(self, world, respawn_point_name=None):
		if respawn_point_name is not None:
			for obj in self.object._v_server.db.world_data[world[0]].objects.values():
				if obj.lot == 4945 and (not hasattr(obj, "respawn_name") or respawn_point_name == "" or obj.respawn_name == respawn_point_name): # respawn point lot
					self.object.physics.position.update(obj.physics.position)
					self.object.physics.rotation.update(obj.physics.rotation)
					break
			else:
				self.object.physics.position.update(self.object._v_server.db.world_data[world[0]].spawnpoint[0])
				self.object.physics.rotation.update(self.object._v_server.db.world_data[world[0]].spawnpoint[1])
			self.object.physics.attr_changed("position")
			self.object.physics.attr_changed("rotation")
			self.object._v_server.commit()

		server_address = await self.object._v_server.address_for_world(world)
		log.info("Sending redirect to world %s", server_address)
		redirect = BitStream()
		redirect.write_header(WorldClientMsg.Redirect)
		redirect.write(server_address[0], char_size=1, allocated_length=33)
		redirect.write(c_ushort(server_address[1]))
		redirect.write(c_bool(False))
		self.object._v_server.send(redirect, self.address)

	def add_mission(self, mission_id):
		mission_progress = MissionProgress(mission_id, self.object._v_server.db.missions[mission_id])
		self.missions.append(mission_progress)
		self.object._v_server.send_game_message(self.notify_mission, mission_id, mission_state=mission_progress.state, sending_rewards=False, address=self.address)
		# obtain item task: update according to items already in inventory
		for task in mission_progress.tasks:
			if task.type == TaskType.ObtainItem:
				for item in self.object.inventory.items:
					if item is not None and item.lot in task.target:
						mission_progress.increment_task(task, self.object, increment=item.amount)
						if task.value == task.target_value:
							break

		self.object._v_server.commit()

	# I'm going to put all game messages that are player-only but which i'm not sure of the component here

	def teleport(self, address, ignore_y:c_bit=True, set_rotation:c_bit=False, skip_all_checks:c_bit=False, pos:Vector3=None, use_navmesh:c_bit=False, w:c_float=1, x:c_float=None, y:c_float=None, z:c_float=None):
		pass

	def drop_client_loot(self, address, use_position:c_bit=False, final_position:Vector3=Vector3.zero, currency:c_int=None, item_template:c_int=None, loot_id:c_int64=None, owner:c_int64=None, source_obj:c_int64=None, spawn_position:Vector3=Vector3.zero):
		pass

	def set_currency(self, address, currency:c_int64=None, loot_type:c_int=0, position:Vector3=None, source_lot:c_int=-1, source_object:c_int64=0, source_trade_id:c_int64=0, source_type:c_int=0):
		self.currency = currency

	def pickup_currency(self, address, currency:c_uint=None, position:Vector3=None):
		self.object._v_server.send_game_message(self.set_currency, currency=self.currency + currency, position=Vector3.zero, address=self.address)

	def pickup_item(self, address, loot_object_id:c_int64=None, player_id:c_int64=None):
		assert player_id == self.object.object_id
		lot = self.object._v_server.dropped_loot[player_id][loot_object_id]
		if lot in (177, 935, 4035, 6431, 7230, 8200, 8208, 11910, 11911, 11912, 11913, 11914, 11915, 11916, 11917, 11918, 11919, 11920): # powerup
			for skill_id in self.object._v_server.db.object_skills[lot]:
				behavior = self.object._v_server.db.skill_behavior[skill_id]
				self.object.skill.handle_behavior(behavior, b"", self.object)
		else:
			self.object.inventory.add_item_to_inventory(lot)
		del self.object._v_server.dropped_loot[player_id][loot_object_id]

	def request_resurrect(self, address):
		self.object._v_server.send_game_message(self.object.destructible.resurrect, broadcast=True)
		self.object.stats.life = 4
		self.object.stats.imagination = 6

	def knockback(self, address, caster:c_int64=0, originator:c_int64=0, knock_back_time_ms:c_int=0, vector:Vector3=None):
		pass

	def offer_mission(self, address, mission_id:c_int=None, offerer:c_int64=None):
		pass

	def respond_to_mission(self, address, mission_id:c_int=None, player_id:c_int64=None, receiver:c_int64=None, reward_item:c_int=-1):
		if reward_item != -1:
			for mission in self.missions:
				if mission.id == mission_id:
					for lot, amount in mission.rew_items:
						if lot == reward_item:
							self.object.inventory.add_item_to_inventory(lot, amount, source_type=LootType.Mission)
							break
		obj = self.object._v_server.game_objects[receiver]
		for comp in obj.components:
			if hasattr(comp, "respond_to_mission"):
				comp.respond_to_mission(address, mission_id, self.object, reward_item)

	def notify_mission(self, address, mission_id:c_int=None, mission_state:c_int=None, sending_rewards:c_bit=False):
		pass

	def notify_mission_task(self, address, mission_id:c_int=None, task_mask:c_int=None, updates:(c_ubyte, c_float)=None):
		pass

	def terminate_interaction(self, address, obj_id_terminator:c_int64=None, type:c_int=None):
		pass

	def request_use(self, address, is_multi_interact_use:c_bit=None, multi_interact_id:c_uint=None, multi_interact_type:c_int=None, object_id:c_int64=None, secondary:c_bit=False):
		if not is_multi_interact_use:
			assert multi_interact_id == 0
			multi_interact_id = None
		assert object_id != 0
		assert not secondary
		obj = self.object._v_server.get_object(object_id)
		if not obj:
			return
		handled = False
		for comp in obj.components:
			if hasattr(comp, "on_use"):
				handled = True
				if comp.on_use(self.object, multi_interact_id):
					break
		if not handled:
			log.warning("Object %s has no interaction callback", obj)

		# update missions that have interacting with this object as requirement
		for mission in self.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.Interact and task.target == obj.lot:
						mission.increment_task(task, self.object)

	def client_item_consumed(self, address, item_id:c_int64=None):
		for item in self.object.inventory.items:
			if item is not None and item.object_id == item_id:
				for mission in self.missions:
					if mission.state == MissionState.Active:
						for task in mission.tasks:
							if task.type == TaskType.UseConsumable and task.target == item.lot:
									mission.increment_task(task, self.object)
				break

	def get_flag(self, flag_id):
		return bool(self.flags & (1 << flag_id))

	def set_flag(self, address, flag:c_bit=None, flag_id:c_int=None):
		if self.get_flag(flag_id) == flag:
			return

		self.flags ^= (-flag ^ self.flags) & (1 << flag_id)
		if flag:
			# update missions that have this flag as requirement
			for mission in self.missions:
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.Flag and flag_id in task.target:
							mission.increment_task(task, self.object)


	def player_loaded(self, address, player_id:c_int64=None):
		pass

	def player_ready(self, address):
		pass

	def display_message_box(self, address, show:c_bit=None, callback_client:c_int64=None, identifier:"wstr"=None, image_id:c_int=None, text:"wstr"=None, user_data:"wstr"=None):
		pass

	def set_jet_pack_mode(self, address, bypass_checks:c_bit=True, hover:c_bit=False, enable:c_bit=False, effect_id:c_uint=-1, air_speed:c_float=10, max_air_speed:c_float=15, vertical_velocity:c_float=1, warning_effect_id:c_uint=-1):
		pass

	def display_tooltip(self, address, do_or_die:c_bit=False, no_repeat:c_bit=False, no_revive:c_bit=False, is_property_tooltip:c_bit=False, show:c_bit=None, translate:c_bit=False, time:c_int=None, id:"wstr"=None, localize_params:"ldf"=None, str_image_name:"wstr"=None, str_text:"wstr"=None):
		pass

	def use_non_equipment_item(self, address, item_to_use:c_int64=None):
		for item in self.object.inventory.items:
			if item is not None and item.object_id == item_to_use:
				for component_type, component_id in self.object._v_server.db.components_registry[item.lot]:
					if component_type == 53: # PackageComponent, make an enum for this somewhen
						self.object.inventory.remove_item_from_inv(InventoryType.Items, item)
						for loot_table in self.object._v_server.db.package_component[component_id]:
							for lot, _ in loot_table[0]:
								self.object.inventory.add_item_to_inventory(lot)
						return

	def notify_pet_taming_minigame(self, address, pet_id:c_int64=None, player_taming_id:c_int64=None, force_teleport:c_bit=None, notify_type:c_uint=None, pets_dest_pos:Vector3=None, tele_pos:Vector3=None, tele_rot:Quaternion=Quaternion.identity):
		pass

	def client_exit_taming_minigame(self, address, voluntary_exit:c_bit=True):
		self.object._v_server.send_game_message(self.notify_pet_taming_minigame, pet_id=0, player_taming_id=0, force_teleport=False, notify_type=PetTamingNotify.Quit, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation, address=address)

	def pet_taming_try_build_result(self, address, success:c_bit=True, num_correct:c_int=0):
		pass

	def notify_pet_taming_puzzle_selected(self, address, bricks:(c_uint, c_uint)=None):
		pass

	def set_emote_lock_state(self, address, lock:c_bit=None, emote_id:c_int=None):
		if not lock:
			self.unlocked_emotes.append(emote_id)

	def toggle_ghost_reference_override(self, address, override:c_bit=False):
		pass

	def set_ghost_reference_position(self, address, position:Vector3=None):
		pass

	def update_model_from_client(self, address, model_id:c_int64=None, position:Vector3=None, rotation:Quaternion=Quaternion.identity):
		for model in self.object.inventory.models:
			if model is not None and model.object_id == model_id:
				spawner_id = self.object._v_server.new_object_id()
				rotation = Quaternion(rotation.y, rotation.z, rotation.w, rotation.x) # don't ask me why this is swapped
				self.object._v_server.db.properties[self.object._v_server.world_id[0]][self.object._v_server.world_id[2]][spawner_id] = model.lot, position, rotation
				self.object._v_server.spawn_model(spawner_id, model.lot, position, rotation)
				self.object.inventory.remove_item_from_inv(InventoryType.Models, model)
				break

	def delete_model_from_client(self, address, model_id:c_int64=0, reason:c_uint=DeleteReason.PickingModelUp):
		assert reason in (DeleteReason.PickingModelUp, DeleteReason.ReturningModelToInventory)
		self.object._v_server.destruct(self.object._v_server.game_objects[model_id])
		for spawner, model in self.object._v_server.models:
			if model.object_id == model_id:
				self.object._v_server.models.remove((spawner, model))
				prop_spawners = self.object._v_server.db.properties[self.object._v_server.world_id[0]][self.object._v_server.world_id[2]]
				del prop_spawners[spawner.object_id]
				item = self.object.inventory.add_item_to_inventory(model.lot)
				if reason == DeleteReason.PickingModelUp:
					self.inventory.equip_inventory(None, item_to_equip=item.object_id)
					self.object._v_server.send_game_message(self.handle_u_g_c_equip_post_delete_based_on_edit_mode, inv_item=item.object_id, items_total=item.amount, address=address)
				break

	def parse_chat_message(self, address, client_state:c_int, text:"wstr"):
		if text[0] == "/":
			self.object._v_server.chat.parse_command(text[1:], self.object)

	def ready_for_updates(self, address, object_id:c_int64=None):
		pass

	def bounce_notification(self, address, object_id_bounced:c_int64=None, object_id_bouncer:c_int64=None, success:c_bit=None):
		pass

	def b_b_b_save_request(self, address, local_id:c_int64=None, lxfml_data_compressed:BitStream=None, time_taken_in_ms:c_uint=None):
		save_response = BitStream()
		save_response.write_header(WorldClientMsg.BlueprintSaveResponse)
		save_response.write(c_int64(local_id))
		save_response.write(c_uint(0))
		save_response.write(c_uint(1))
		save_response.write(c_int64(self.object._v_server.new_object_id()))
		save_response.write(c_uint(len(lxfml_data_compressed)))
		save_response.write(lxfml_data_compressed)
		self.object._v_server.send(save_response, address)

	def start_arranging_with_item(self, address, first_time:c_bit=True, build_area_id:c_int64=0, build_start_pos:Vector3=None, source_bag:c_int=None, source_id:c_int64=None, source_lot:c_int=None, source_type:c_int=None, target_id:c_int64=None, target_lot:c_int=None, target_pos:Vector3=None, target_type:c_int=None):
		pass

	def finish_arranging_with_item(self, build_area_id:c_int64=0, new_source_bag:c_int=None, new_source_id:c_int64=None, new_source_lot:c_int=None, new_source_type:c_int=None, new_target_id:c_int64=None, new_target_lot:c_int=None, new_target_type:c_int=None, new_target_pos:Vector3=None, old_item_bag:c_int=None, old_item_id:c_int64=None, old_item_lot:c_int=None, old_item_type:c_int=None):
		pass

	def u_i_message_server_to_single_client(self, address, args:"amf"=None, str_message_name:"str"=None):
		pass

	def pet_taming_try_build(self, address, selections:(c_uint, c_uint64)=None, client_failed:c_bit=False):
		if not client_failed:
			self.object._v_server.send_game_message(self.pet_taming_try_build_result, address=address)
			self.object._v_server.send_game_message(self.notify_pet_taming_minigame, pet_id=0, player_taming_id=0, force_teleport=False, notify_type=PetTamingNotify.NamingPet, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation, address=self.address)

	def report_bug(self, address, body:"wstr"=None, client_version:"str"=None, other_player_id:"str"=None, selection:"str"=None):
		for account in self.object._v_server.accounts.values():
			self.object._v_server.mail.send_mail(self.name, "Bug Report: "+selection, body, account.characters.selected())

	def request_smash_player(self, address):
		self.object.destructible.request_die(None, unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=self.object.object_id, loot_owner_id=0)

	def handle_u_g_c_equip_post_delete_based_on_edit_mode(self, address, inv_item:c_int64=None, items_total:c_int=0):
		pass

	def property_contents_from_client(self, address, query_db:c_bit=False):
		self.object._v_server.send_game_message(self.get_models_on_property, models={model.object_id:spawner.object_id for spawner, model in self.object._v_server.models}, address=address)

	def get_models_on_property(self, address, models:(c_uint, c_int64, c_int64)=None):
		pass

	def match_request(self, address, activator:c_int64=None, player_choices:"ldf"=None, type:c_int=None, value:c_int=None):
		# todo: how does the server know which matchmaking activity the client wants?
		self.object._v_server.send_game_message(self.match_response, response=0, address=address)
		if type == MatchRequestType.Join and value == MatchRequestValue.Join:
			update_data = {}
			update_data["time"] = c_float, 60
			self.object._v_server.send_game_message(self.match_update, data=update_data, type=MatchUpdateType.Time, address=address)
		elif type == MatchRequestType.Ready and value == MatchRequestValue.Ready:
			asyncio.ensure_future(self.transfer_to_world((1101, 0, 0)))

	def match_response(self, address, response:c_int=None):
		pass

	def match_update(self, address, data:"ldf"=None, type:c_int=None):
		pass

	def used_information_plaque(self, address, plaque_object_id:c_int64=None):
		pass

	def activate_brick_mode(self, address, build_object_id:c_int64=0, build_type:c_int=BuildType.BuildOnProperty, enter_build_from_world:c_bit=True, enter_flag:c_bit=True):
		pass

	def modify_lego_score(self, address, score:c_int64=None, source_type:c_int=0):
		self.universe_score += score
		if self.universe_score > self.object._v_server.db.level_scores[self.level]:
			self.level += 1

	def restore_to_post_load_stats(self, address):
		pass

	def set_rail_movement(self, address, path_go_forward:c_bit=None, path_name:"wstr"=None, path_start:c_uint=None, rail_activator_component_id:c_int=-1, rail_activator_obj_id:c_int64=0):
		pass

	def start_rail_movement(self, address, damage_immune:c_bit=True, no_aggro:c_bit=True, notify_activator:c_bit=False, show_name_billboard:c_bit=True, camera_locked:c_bit=True, collision_enabled:c_bit=True, loop_sound:"wstr"=None, path_go_forward:c_bit=True, path_name:"wstr"=None, path_start:c_uint=0, rail_activator_component_id:c_int=-1, rail_activator_obj_id:c_int64=0, start_sound:"wstr"=None, stop_sound:"wstr"=None, use_db:c_bit=True):
		pass

	def start_celebration_effect(self, address, animation:"wstr"=None, background_object:c_int=11164, camera_path_lot:c_int=12458, cele_lead_in:c_float=1, cele_lead_out:c_float=0.8, celebration_id:c_int=-1, duration:c_float=None, icon_id:c_uint=None, main_text:"wstr"=None, mixer_program:"str"=None, music_cue:"str"=None, path_node_name:"str"=None, sound_guid:"str"=None, sub_text:"wstr"=None):
		pass

	def server_done_loading_all_objects(self, address):
		pass

	def notify_server_level_processing_complete(self, address):
		self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="7074", effect_type="create", effect_id=7074, broadcast=True)
