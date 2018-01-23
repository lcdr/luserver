import asyncio
import logging
import random
from collections import Counter

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from pyraknet.bitstream import c_bit, c_bool, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from ...amf3 import AMF3
from ...auth import GMLevel
from ...bitstream import WriteStream
from ...game_object import broadcast, c_int_, c_int64_, c_uint_, GameObject, single
from ...messages import WorldClientMsg
from ...world import server, World
from ...math.quaternion import Quaternion
from ...math.vector import Vector3
from ...modules.social import FriendUpdateType
from ..component import Component
from ..inventory import InventoryType
from ..mission import MissionState, TaskType
from .activity import CharActivity
from .camera import CharCamera
from .mission import CharMission
from .pet import CharPet
from .property import CharProperty
from .trade import CharTrade
from .ui import CharUI

from builtins import property

log = logging.getLogger(__name__)

FACTION_TOKEN_PROXY = 13763
ASSEMBLY_TOKEN = 8318
SENTINEL_TOKEN = 8319
PARADOX_TOKEN = 8320
VENTURE_LEAGUE_TOKEN = 8321

VENTURE_LEAGUE_FLAG = 46
ASSEMBLY_FLAG = 47
PARADOX_FLAG = 48
SENTINEL_FLAG = 49

class TerminateType:
	Range = 0
	User = 1
	FromInteraction = 2

class BuildType:
	BuildNowhere = 0
	BuildInWorld = 1
	BuildOnProperty = 2

class RewardType:
	Item = 0
	InventorySpace = 4

class CharacterComponent(Component, CharActivity, CharCamera, CharMission, CharPet, CharProperty, CharTrade, CharUI):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.char = self

		# DB stuff

		self.account = None
		self.address = None
		self._online = False
		self._world = 0, 0, 0
		self.currency = 0 # todo: consider whether a property with set_currency is possible
		self.friends = PersistentList()
		self.mails = PersistentList()

		self.unlocked_emotes = PersistentList()

		self.clone_id = server.new_clone_id()

		for world in (World.BlockYard, World.AvantGrove, World.NimbusRock, World.NimbusIsle, World.ChanteyShanty, World.RavenBluff):
			server.db.properties[world.value][self.clone_id] = PersistentMapping()

		self.dropped_loot = {}
		self.last_collisions = []

		CharMission.__init__(self)
		CharTrade.__init__(self)

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

		self.traveling_rocket = None

		self._flags["pvp_enabled"] = "gm_flag"
		self._flags["show_gm_status"] = "gm_flag"
		self.pvp_enabled = False
		self.show_gm_status = False

		self._flags["rebuilding"] = "rebuilding_flag"
		self.rebuilding = 0

		self._flags["tags"] = "guild_flag"
		self.tags = PersistentList()

	def serialize(self, out, is_creation):
		# First index
		creation = is_creation and self.vehicle_id != 0
		out.write(c_bit(creation or self.vehicle_flag))
		if creation or self.vehicle_flag:
			out.write(c_bit(creation or self.vehicle_id_flag))
			if creation or self.vehicle_id_flag:
				out.write(c_int64(self.vehicle_id))
				if not creation:
					self.vehicle_id_flag = False
			out.write(c_ubyte(1)) # unknown
			if not creation:
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
			out.write(c_bit(self.traveling_rocket is not None))
			if self.traveling_rocket is not None:
				module_str = ""
				for module in self.traveling_rocket:
					module_str += "1:%i;" % module
				out.write(module_str, length_type=c_ushort)
				self.traveling_rocket = None

		out.write(c_bit(self.gm_flag or is_creation))
		if self.gm_flag or is_creation:
			out.write(c_bit(self.pvp_enabled))
			out.write(c_bit(self.show_gm_status))
			if self.account is None:
				out.write(c_ubyte(0))
			else:
				out.write(c_ubyte(self.account.gm_level))
			out.write(c_bit(False))
			out.write(c_ubyte(0))
			if self.gm_flag:
				self.gm_flag = False

		out.write(c_bit(self.rebuilding_flag or is_creation))
		if self.rebuilding_flag or is_creation:
			out.write(c_uint(self.rebuilding))
			if self.rebuilding_flag:
				self.rebuilding_flag = False

		out.write(c_bit(self.guild_flag or (is_creation and self.tags)))
		if self.guild_flag or (is_creation and self.tags):
			if self.tags:
				out.write(c_int64(self.object.object_id))
			else:
				out.write(c_int64(0))
			out.write(", ".join(self.tags), length_type=c_ubyte)
			out.write(c_bit(False))
			out.write(c_int(-1))
			if self.guild_flag:
				self.guild_flag = False

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
		update_notify = WriteStream()
		update_notify.write_header(WorldClientMsg.FriendUpdateNotify)
		update_notify.write(c_ubyte(update_type))
		update_notify.write(self.object.name, allocated_length=33)
		update_notify.write(c_ushort(self.world[0]))
		update_notify.write(c_ushort(self.world[1]))
		update_notify.write(c_uint(self.world[2]))
		update_notify.write(c_bool(False)) # is best friend
		update_notify.write(c_bool(False)) # is FTP

		outdated_refs = []
		for index, friend_ref in enumerate(self.friends):
			if friend_ref() is None:
				outdated_refs.insert(0, index)
			else:
				if friend_ref().char.address in server._server._connected:
					server.send(update_notify, friend_ref().char.address)

		for index in outdated_refs:
			del self.friends[index]

	def on_destruction(self):
		self.object._handlers.clear()
		self.vehicle_id = 0
		self.online = False
		self.dropped_loot.clear()
		self.last_collisions.clear()
		CharTrade.on_destruction(self)
		self.check_for_leaks()

	def check_for_leaks(self, fullcheck=False):
		if len(self.object.inventory.equipped) > 1:
			log.warning("Multiple equipped states")
			for _ in range(len(self.object.inventory.equipped)-1):
				self.object.inventory.equipped.pop()
		elif not self.object.inventory.equipped:
			log.warning("No equipped state")
			self.object.inventory.equipped.append(PersistentList())

		clean_equipped = False
		item_types_equipped = set()
		for item in self.object.inventory.equipped[-1]:
			if item.item_type in item_types_equipped:
				log.warning("Multiple items of same type equipped: %s", item)
				clean_equipped = True
			else:
				item_types_equipped.add(item.item_type)

			if item.count <= 0:
				log.warning("Item equipped with count %i: %s", item.count, item)
				clean_equipped = True

		if clean_equipped:
			log.info(self.object.inventory.equipped[-1])
			for item in self.object.inventory.equipped[-1]:
				self.object.inventory.un_equip_inventory(item_to_unequip=item.object_id)

		if fullcheck:
			for inv in (self.object.inventory.items, self.object.inventory.temp_items, self.object.inventory.models):
				for item in inv:
					if item is not None and item.count <= 0:
						log.warning("Item in inventory with count %i: %s", item.count, item)

		if self.object.inventory.temp_models:
			log.warning("Temp Models not empty")
			log.warning(self.object.inventory.temp_models)

	def faction_token_lot(self):
		if self.get_flag(VENTURE_LEAGUE_FLAG):
			return VENTURE_LEAGUE_TOKEN
		if self.get_flag(ASSEMBLY_FLAG):
			return ASSEMBLY_TOKEN
		if self.get_flag(PARADOX_FLAG):
			return PARADOX_TOKEN
		if self.get_flag(SENTINEL_FLAG):
			return SENTINEL_TOKEN

	def random_loot(self, loot_matrix):
		loot = Counter()
		roll = random.random()
		for table_index, percent, min_to_drop, max_to_drop in loot_matrix:
			if roll < percent:
				for _ in range(random.randint(min_to_drop, max_to_drop)):
					lot, mission_drop, _ = random.choice(server.db.loot_table[table_index])
					if lot == FACTION_TOKEN_PROXY:
						lot = self.faction_token_lot()
						if lot is None:
							continue
					if mission_drop and not self.should_be_dropped(lot):
						continue
					loot[lot] += 1
		return loot

	def should_be_dropped(self, lot):
		for mission in self.missions.values():
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.ObtainItem and lot in task.target and task.value < task.target_value:
						return True
		return False

	async def transfer_to_world(self, world, respawn_point_name=None, include_self=False):
		server.commit()
		# needed for ZODB to pick up the changes to the components
		# normally not needed because a replica serialization autotriggers this
		self.object._p_changed = True

		if respawn_point_name is not None and world[0] in server.db.world_data:
			for obj in server.db.world_data[world[0]].objects.values():
				if obj.lot == 4945 and (not hasattr(obj, "respawn_name") or respawn_point_name == "" or obj.respawn_name == respawn_point_name): # respawn point lot
					self.object.physics.position.update(obj.physics.position)
					self.object.physics.rotation.update(obj.physics.rotation)
					break
			else:
				self.object.physics.position.update(server.db.world_data[world[0]].spawnpoint[0])
				self.object.physics.rotation.update(server.db.world_data[world[0]].spawnpoint[1])
			self.object.physics.attr_changed("position")
			self.object.physics.attr_changed("rotation")
		server.commit()

		server_address = await server.address_for_world(world, include_self)
		log.info("Sending redirect to world %s", server_address)
		redirect = WriteStream()
		redirect.write_header(WorldClientMsg.Redirect)
		redirect.write(server_address[0].encode("latin1"), allocated_length=33)
		redirect.write(c_ushort(server_address[1]))
		redirect.write(c_bool(False))
		server.send(redirect, self.address)

	async def transfer_to_last_non_instance(self, position=None, rotation=None):
		if position is not None:
			self.object.physics.position.update(position)
			self.object.physics.attr_changed("position")
		if rotation is not None:
			self.object.physics.rotation.update(rotation)
			self.object.physics.attr_changed("rotation")
		await self.transfer_to_world(((self.world[0] // 100)*100, self.world[1], 0))

	def mount(self, vehicle):
		vehicle.comp_108.driver_id = self.object.object_id
		self.vehicle_id = vehicle.object_id

	def dismount(self):
		if self.vehicle_id != 0:
			server.game_objects[self.vehicle_id].comp_108.driver_id = 0
			self.vehicle_id = 0

	# I'm going to put all game messages that are player-only but which i'm not sure of the component here

	@single
	def teleport(self, ignore_y:bool=True, set_rotation:bool=False, skip_all_checks:bool=False, pos:Vector3=None, use_navmesh:bool=False, w:float=1, x:float=None, y:float=None, z:float=None):
		pass

	@single
	def drop_client_loot(self, use_position:bool=False, final_position:Vector3=Vector3.zero, currency:c_int_=None, item_template:c_int_=None, loot_id:c_int64_=None, owner:GameObject=None, source_obj:GameObject=None, spawn_position:Vector3=Vector3.zero):
		pass

	def play_emote(self, emote_id:c_int_, target:GameObject):
		self.emote_played(emote_id, target)
		if target is not None:
			target.handle("on_emote_received", self.object, emote_id, silent=True)
			self.update_mission_task(TaskType.UseEmote, target.lot, emote_id)

	@single
	def set_currency(self, currency:c_int64_=None, loot_type:c_int_=0, position:Vector3=None, source_lot:c_int_=-1, source_object:GameObject=0, source_trade:GameObject=0, source_type:c_int_=0):
		self.currency = currency

	def pickup_currency(self, currency:c_uint_=None, position:Vector3=None):
		self.set_currency(currency=self.currency + currency, position=Vector3.zero)

	def pickup_item(self, loot_object_id:c_int64_=None, player_id:c_int64_=None):
		assert player_id == self.object.object_id
		if loot_object_id not in self.dropped_loot:
			return
		lot = self.dropped_loot[loot_object_id]
		if lot in (177, 935, 4035, 6431, 7230, 8200, 8208, 11910, 11911, 11912, 11913, 11914, 11915, 11916, 11917, 11918, 11919, 11920): # powerup
			for skill_id, _ in server.db.object_skills[lot]:
				self.object.skill.cast_skill(skill_id)
				self.update_mission_task(TaskType.CollectPowerup, skill_id)
		else:
			self.object.inventory.add_item(lot)
		del self.dropped_loot[loot_object_id]

	def request_resurrect(self):
		self.object.destructible.resurrect()
		self.object.stats.life = 4
		self.object.stats.imagination = 6

	@broadcast
	def knockback(self, caster:GameObject=0, originator:GameObject=0, knock_back_time_ms:c_int_=0, vector:Vector3=None):
		pass

	@single
	def terminate_interaction(self, terminator:GameObject=None, type:c_int_=None):
		pass

	def request_use(self, is_multi_interact_use:bool=None, multi_interact_id:c_uint_=None, multi_interact_type:c_int_=None, obj:GameObject=None, secondary:bool=False):
		if not is_multi_interact_use:
			assert multi_interact_id == 0
			multi_interact_id = None
		assert not secondary
		if obj is None:
			return
		log.debug("Interacting with %s", obj)
		obj.handle("on_use", self.object, multi_interact_id)

		self.update_mission_task(TaskType.Interact, obj.lot)

	@broadcast
	def emote_played(self, emote_id:c_int_, target:GameObject):
		pass

	def client_item_consumed(self, item_id:c_int64_=None):
		item = self.object.inventory.get_stack(InventoryType.Items, item_id)
		self.update_mission_task(TaskType.UseConsumable, item.lot)

	@single
	def set_user_ctrl_comp_pause(self, paused:bool=None):
		pass

	def get_flag(self, flag_id):
		return bool(self.flags & (1 << flag_id))

	@single
	def set_flag(self, flag:bool=None, flag_id:c_int_=None):
		if self.get_flag(flag_id) == flag:
			return

		self.flags ^= (-int(flag) ^ self.flags) & (1 << flag_id)
		if flag:
			self.update_mission_task(TaskType.Flag, flag_id)

	def player_loaded(self, player_id:c_int64_=None):
		assert player_id == self.object.object_id
		self.player_ready()
		if self.world == (0, 0, 0):
			server.chat.system_message(server.db.config["new_char_message"], self.address, broadcast=False)
		self.world = server.world_id

		for item in self.object.inventory.equipped[-1]:
			self.object.skill.add_skill_for_item(item, add_buffs=False)

		self.restore_to_post_load_stats()
		server.world_control_object.handle("player_ready", player=self.object)

	@single
	def player_ready(self):
		pass

	@single
	def set_gravity_scale(self, scale:float=None):
		pass

	@broadcast
	def set_jet_pack_mode(self, bypass_checks:bool=True, hover:bool=False, enable:bool=False, effect_id:c_uint_=-1, air_speed:float=10, max_air_speed:float=15, vertical_velocity:float=1, warning_effect_id:c_uint_=-1):
		pass

	def use_non_equipment_item(self, item_to_use:c_int64_=None):
		item = self.object.inventory.get_stack(InventoryType.Items, item_to_use)
		for component_type, component_id in server.db.components_registry[item.lot]:
			if component_type == 53: # PackageComponent, make an enum for this somewhen
				self.object.inventory.remove_item(InventoryType.Items, item)
				for lot, count in self.random_loot(server.db.package_component[component_id]).items():
					asyncio.get_event_loop().call_soon(self.object.inventory.add_item, lot, count)
				return

	@single
	def set_emote_lock_state(self, lock:bool=None, emote_id:c_int_=None):
		if not lock:
			self.unlocked_emotes.append(emote_id)

	def parse_chat_message(self, client_state:c_int_, text:str):
		if text.startswith("/"):
			server.chat.parse_command(text[1:], self.object)

	def ready_for_updates(self, object_id:c_int64_=None):
		pass

	def bounce_notification(self, object_id_bounced:c_int64_=None, object_id_bouncer:c_int64_=None, success:bool=None):
		pass

	@single
	def display_zone_summary(self, is_property_map:bool=False, is_zone_start:bool=False, sender:GameObject=None):
		pass

	@broadcast
	def start_arranging_with_item(self, first_time:bool=True, build_area:GameObject=0, build_start_pos:Vector3=None, source_bag:c_int_=None, source_id:c_int64_=None, source_lot:c_int_=None, source_type:c_int_=None, target_id:c_int64_=None, target_lot:c_int_=None, target_pos:Vector3=None, target_type:c_int_=None):
		self.object.inventory.push_equipped_items_state()

	@broadcast
	def finish_arranging_with_item(self, build_area_id:c_int64_=0, new_source_bag:c_int_=None, new_source_id:c_int64_=None, new_source_lot:c_int_=None, new_source_type:c_int_=None, new_target_id:c_int64_=None, new_target_lot:c_int_=None, new_target_type:c_int_=None, new_target_pos:Vector3=None, old_item_bag:c_int_=None, old_item_id:c_int64_=None, old_item_lot:c_int_=None, old_item_type:c_int_=None):
		pass

	@single
	def u_i_message_server_to_single_client(self, args:AMF3=None, message_name:bytes=None):
		pass

	def report_bug(self, body:str=None, client_version:bytes=None, other_player_id:bytes=None, selection:bytes=None):
		# The chat text input has limited length, this one doesn't
		# So this makes use of that to allow longer chat commands
		if selection == b"%[UI_HELP_IN_GAME]" and body.startswith("/"):
			self.parse_chat_message(0, body)
			return
		for account in server.accounts.values():
			if account.gm_level == GMLevel.Admin:
				for char in account.characters.values():
					server.mail.send_mail(self.object.name, "Bug Report: "+selection.decode(), body, char)

	def request_smash_player(self):
		self.object.destructible.simply_die(killer=self.object)

	@broadcast
	def toggle_g_m_invis(self, state_out:c_bit=False):
		pass

	@broadcast
	def player_reached_respawn_checkpoint(self, pos:Vector3=None, rot:Quaternion=Quaternion.identity):
		pass

	def used_information_plaque(self, plaque_object_id:c_int64_=None):
		pass

	@single
	def activate_brick_mode(self, build_object_id:c_int64_=0, build_type:c_int_=BuildType.BuildOnProperty, enter_build_from_world:bool=True, enter_flag:bool=True):
		pass

	@single
	def modify_lego_score(self, score:c_int64_=None, source_type:c_int_=0):
		self.universe_score += score
		if self.level < len(server.db.level_scores) and self.universe_score > server.db.level_scores[self.level]:
			self.level += 1
			if self.level in server.db.level_rewards:
				self.notify_level_rewards(self.level, sending_rewards=True)
				for reward_type, value in server.db.level_rewards[self.level]:
					if reward_type == RewardType.Item:
						self.object.inventory.add_item(value, source_type=source_type)
					elif reward_type == RewardType.InventorySpace:
						self.object.inventory.set_inventory_size(inventory_type=InventoryType.Items, size=len(self.object.inventory.items)+value)
					else:
						log.warning("Level reward type %i not implemented", reward_type)
				self.notify_level_rewards(self.level, sending_rewards=False)

	@single
	def restore_to_post_load_stats(self):
		pass

	@single
	def set_rail_movement(self, path_go_forward:bool=None, path_name:str=None, path_start:c_uint_=None, rail_activator_component_id:c_int_=-1, rail_activator_obj_id:c_int64_=0):
		pass

	@single
	def start_rail_movement(self, damage_immune:bool=True, no_aggro:bool=True, notify_activator:bool=False, show_name_billboard:bool=True, camera_locked:bool=True, collision_enabled:bool=True, loop_sound:str=None, path_go_forward:bool=True, path_name:str=None, path_start:c_uint_=0, rail_activator_component_id:c_int_=-1, rail_activator:GameObject=0, start_sound:str=None, stop_sound:str=None, use_db:bool=True):
		pass

	@single
	def start_celebration_effect(self, animation:str=None, background_object:c_int_=11164, camera_path_lot:c_int_=12458, cele_lead_in:float=1, cele_lead_out:float=0.8, celebration_id:c_int_=-1, duration:float=None, icon_id:c_uint_=None, main_text:str=None, mixer_program:bytes=None, music_cue:bytes=None, path_node_name:bytes=None, sound_guid:bytes=None, sub_text:str=None):
		pass

	@single
	def server_done_loading_all_objects(self):
		pass

	def notify_server_level_processing_complete(self):
		self.object.render.play_f_x_effect(name=b"7074", effect_type="create", effect_id=7074)

	@single
	def notify_level_rewards(self, level:c_int_=None, sending_rewards:bool=False):
		pass
