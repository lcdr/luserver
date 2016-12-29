import configparser
import os
import sqlite3
import time
from types import SimpleNamespace

import BTrees
import transaction
import ZEO

from luserver.world import World
from luserver.components.inventory import ItemType
from luserver.components.mission import TaskType
from luserver.components.skill import BehaviorTemplate

import luz_importer
import scripts

config = configparser.ConfigParser()
config.read("../luserver.ini")


# temporarily using int instead of bool for faster editing
GENERATE_ACCOUNTS = 1
GENERATE_SKILLS = 1
GENERATE_MISSIONS = 1
GENERATE_COMPS = 1
GENERATE_WORLD_DATA = 1

while True:
	try:
		conn = ZEO.connection(12345, wait_timeout=3)
		break
	except ZEO.Exceptions.ClientDisconnected:
		os.system(r"start runzeo -a 12345 -f ./server_db.db")
		time.sleep(3)

root = conn.root

if GENERATE_ACCOUNTS:
	root.current_object_id = 1
	root.current_clone_id = 1
	root.accounts = BTrees.OOBTree.BTree()
	root.servers = BTrees.OOBTree.BTree()

	root.properties = BTrees.IOBTree.BTree()
	for world in (World.BlockYard, World.AvantGrove, World.NimbusRock, World.NimbusIsle, World.ChanteyShanty, World.RavenBluff):
		root.properties[world.value] = BTrees.OOBTree.BTree()

	# Read-only data
	# All "tables" below don't need things like PersistentList instead of normal list, since they will never be modified

	root.predef_names = []
	for name_part in ("first", "middle", "last"):
		names = []
		with open(os.path.join(config["paths"]["client_path"], "res/names/minifigname_"+name_part+".txt")) as file:
			for name in file:
				names.append(name[:-1])

		root.predef_names.append(names)

cdclient = sqlite3.connect(config["paths"]["cdclient_path"])

if GENERATE_ACCOUNTS:
	root.colors = BTrees.IOBTree.BTree()
	for row in cdclient.execute("select id, validCharacters from BrickColors"):
		root.colors[row[0]] = bool(row[1])

	root.level_scores = tuple(i[0] for i in cdclient.execute("select requiredUScore from LevelProgressionLookup").fetchall())

	root.world_info = BTrees.IOBTree.BTree()
	for world_id, template in cdclient.execute("select zoneID, zoneControlTemplate from ZoneTable"):
		root.world_info[world_id] = template

def get_behavior(behavior_id):
	if behavior_id == 0:
		return None
	behavior_id = int(behavior_id)
	if behavior_id not in root.behavior:
		global behavs_accessed
		behavs_accessed += 1
		if behavior_id not in templates:
			return None
		template_id = templates[behavior_id]
		params = parameters.get(behavior_id, {})
		root.behavior[behavior_id] = behavior = SimpleNamespace(id=behavior_id, template=template_id, **params)

		if template_id in (BehaviorTemplate.AreaOfEffect, BehaviorTemplate.OverTime, BehaviorTemplate.TargetCaster, BehaviorTemplate.Duration, BehaviorTemplate.AttackDelay, BehaviorTemplate.ChargeUp, BehaviorTemplate.Start, BehaviorTemplate.ClearTarget):
			behavior.action = get_behavior(behavior.action)

		if template_id == BehaviorTemplate.BasicAttack:
			if hasattr(behavior, "on_success"):
				if behavior.on_success == 0:
					del behavior.on_success
				else:
					behavior.on_success = get_behavior(behavior.on_success)
		elif template_id == BehaviorTemplate.TacArc:
			if hasattr(behavior, "action"):
				behavior.action = get_behavior(behavior.action)
			if hasattr(behavior, "blocked action"):
				behavior.blocked_action = get_behavior(getattr(behavior, "blocked action"))
				delattr(behavior, "blocked action")
			if hasattr(behavior, "miss action"):
				behavior.miss_action = get_behavior(getattr(behavior, "miss action"))
				delattr(behavior, "miss action")

		elif template_id == BehaviorTemplate.And:
			behavs = []
			for num in range(1, 11):
				if hasattr(behavior, "behavior %i" % num):
					behavs.append(get_behavior(getattr(behavior, "behavior %i" % num)))
					delattr(behavior, "behavior %i" % num)
			behavior.behaviors = tuple(behavs)

		elif template_id == BehaviorTemplate.ProjectileAttack:
			if hasattr(behavior, "spread_count"):
				behavior.spread_count = int(behavior.spread_count)
			behavior.projectile_lot = int(behavior.LOT_ID)
			del behavior.LOT_ID

		elif template_id == BehaviorTemplate.Heal:
			behavior.life = int(behavior.health)
			del behavior.health

		elif template_id == BehaviorTemplate.MovementSwitch:
			behavior.ground_action = get_behavior(behavior.ground_action)
			behavior.jump_action = get_behavior(behavior.jump_action)
			behavior.double_jump_action = get_behavior(behavior.double_jump_action)
			if hasattr(behavior, "air_action"):
				behavior.air_action = get_behavior(behavior.air_action)
			if hasattr(behavior, "falling_action"):
				behavior.falling_action = get_behavior(behavior.falling_action)
			if hasattr(behavior, "jetpack_action"):
				behavior.jetpack_action = get_behavior(behavior.jetpack_action)

		elif template_id == BehaviorTemplate.OverTime:
			behavior.num_intervals = int(behavior.num_intervals)

		elif template_id == BehaviorTemplate.Imagination:
			behavior.imagination = int(behavior.imagination)
		elif template_id == BehaviorTemplate.RepairArmor:
			behavior.armor = int(behavior.armor)

		elif template_id in (BehaviorTemplate.SpawnObject, BehaviorTemplate.SpawnQuickbuild):
			behavior.lot = int(behavior.LOT_ID)
			del behavior.LOT_ID

		elif template_id == BehaviorTemplate.Switch:
			behavior.action_true = get_behavior(behavior.action_true)
			behavior.action_false = get_behavior(behavior.action_false)
			if hasattr(behavior, "isEnemyFaction"):
				behavior.is_enemy_faction = behavior.isEnemyFaction
				del behavior.isEnemyFaction

		elif template_id == BehaviorTemplate.Buff:
			if hasattr(behavior, "life"):
				behavior.life = int(behavior.life)
			if hasattr(behavior, "armor"):
				behavior.armor = int(behavior.armor)
			if hasattr(behavior, "imag"):
				behavior.imagination = int(behavior.imag)
				del behavior.imag

		elif template_id == BehaviorTemplate.Chain:
			behavs = []
			for num in range(1, 5):
				if hasattr(behavior, "behavior %i" % num):
					behavs.append(get_behavior(getattr(behavior, "behavior %i" % num)))
					delattr(behavior, "behavior %i" % num)
			behavior.behaviors = tuple(behavs)

		elif template_id == BehaviorTemplate.ForceMovement:
			if hasattr(behavior, "hit_action"):
				behavior.hit_action = get_behavior(behavior.hit_action)
			if hasattr(behavior, "hit_action_enemy"):
				behavior.hit_action_enemy = get_behavior(behavior.hit_action_enemy)
			if hasattr(behavior, "hit_action_faction"):
				behavior.hit_action_faction = get_behavior(behavior.hit_action_faction)
			if hasattr(behavior, "timeout_action"):
				behavior.timeout_action = get_behavior(behavior.timeout_action)

		elif template_id == BehaviorTemplate.SwitchMultiple:
			behavs = []
			for num in range(1, 5):
				if hasattr(behavior, "behavior %i" % num):
					behavs.append((get_behavior(getattr(behavior, "behavior %i" % num)), getattr(behavior, "value %i" % num)))
					delattr(behavior, "behavior %i" % num)
					delattr(behavior, "value %i" % num)
			behavior.behaviors = tuple(behavs)

		elif template_id == BehaviorTemplate.AirMovement:
			if hasattr(behavior, "ground_action"):
				behavior.ground_action = get_behavior(behavior.ground_action)
			if hasattr(behavior, "hit_action"):
				behavior.hit_action = get_behavior(behavior.hit_action)
			if hasattr(behavior, "hit_action_enemy"):
				behavior.hit_action_enemy = get_behavior(behavior.hit_action_enemy)
			if hasattr(behavior, "timeout_action"):
				behavior.timeout_action = get_behavior(behavior.timeout_action)

	return root.behavior[behavior_id]


if GENERATE_SKILLS:
	behavs_accessed = 0
	templates = {b: t for b, t in cdclient.execute("select behaviorID, templateID from BehaviorTemplate").fetchall()}
	parameters = {}
	for behavior_id, parameter_id, value in cdclient.execute("select behaviorID, parameterID, value from BehaviorParameter"):
		parameters.setdefault(behavior_id, {})[parameter_id] = value

	root.behavior = BTrees.IOBTree.BTree()

	root.object_skills = BTrees.IOBTree.BTree()
	for row in cdclient.execute("select objectTemplate, skillID from ObjectSkills"):
		root.object_skills.setdefault(row[0], []).append(row[1])

	root.skill_behavior = BTrees.IOBTree.BTree()
	for skill_id, behavior_id in cdclient.execute("select skillID, behaviorID from SkillBehavior"):
		root.skill_behavior[skill_id] = get_behavior(behavior_id)
	print("behavs_accessed", behavs_accessed)

if GENERATE_MISSIONS:
	root.missions = BTrees.IOBTree.BTree()
	for id, prereq, currency, universe_score, is_choice_reward, reward_item1, reward_item1_count, reward_item2, reward_item2_count, reward_item3, reward_item3_count, reward_item4, reward_item4_count, reward_emote, reward_max_imagination, reward_max_life, reward_max_items, is_mission in cdclient.execute("select id, prereqMissionID, reward_currency, LegoScore, isChoiceReward, reward_item1, reward_item1_count, reward_item2, reward_item2_count, reward_item3, reward_item3_count, reward_item4, reward_item4_count, reward_emote, reward_maximagination, reward_maxhealth, reward_maxinventory, isMission from Missions"):
		# prereqs
		prereqs = []
		if prereq:
			prereq = prereq.replace("(", "").replace(")", "").replace("&", ",") # normalize pointless syntax
			for i in prereq.split(","):
				prereq_ors = i.split("|")
				prereqs.append(tuple(tuple(int(k) for k in j.split(":")) if ":" in j else int(j) for j in prereq_ors)) # : in prereqs is mission state

		# tasks
		tasks = []
		for task_type, target, target_group, target_value, parameter in cdclient.execute("select taskType, target, targetGroup, targetValue, taskParam1 from MissionTasks where id = "+str(id)):
			if task_type in (TaskType.KillEnemy, TaskType.Script, TaskType.ObtainItem, TaskType.MissionComplete, TaskType.TamePet):
				target = target,
				if target_group:
					target += tuple(int(target_id) for target_id in target_group.split(","))
			elif task_type in (TaskType.UseEmote, TaskType.UseSkill):
				parameter = tuple(int(param_id) for param_id in parameter.split(","))
			elif task_type == TaskType.Discover:
				target = target_group
			elif task_type == TaskType.Flag:
				target = tuple(int(flag_id) for flag_id in target_group.split(","))

			tasks.append((task_type, target, target_value, parameter))

		reward_items = []
		for lot, count in ((reward_item1, reward_item1_count), (reward_item2, reward_item2_count), (reward_item3, reward_item3_count), (reward_item4, reward_item4_count)):
			if lot != -1:
				if count == 0:
					count = 1
				reward_items.append((lot, count))

		if reward_emote == -1:
			reward_emote = None

		root.missions[id] = (currency, universe_score, bool(is_choice_reward), tuple(reward_items), reward_emote, reward_max_life, reward_max_imagination, reward_max_items), tuple(prereqs), tuple(tasks), bool(is_mission)

if GENERATE_COMPS:
	# temporary, not actually needed for the server (therefore dict instead of root assignment)
	currency_table = {}
	for row in cdclient.execute("select currencyIndex, npcminlevel, minvalue, maxvalue from CurrencyTable"):
		currency_table.setdefault(row[0], []).append((row[1], row[2], row[3]))

	loot_matrix = {}
	for row in cdclient.execute("select LootMatrixIndex, LootTableIndex, percent, minToDrop, maxToDrop from LootMatrix"):
		loot_table_entry = []
		for loot_table_row in cdclient.execute("select itemid, sortPriority from LootTable where LootTableIndex == %i" % row[1]):
			loot_table_entry.append((loot_table_row[0], loot_table_row[1]))
		loot_table_entry = tuple(loot_table_entry)
		loot_matrix.setdefault(row[0], []).append((loot_table_entry, row[2], row[3], row[4]))

	activity_rewards = {}
	for object_template, loot_matrix_index, currency_index in cdclient.execute("select objectTemplate, LootMatrixIndex, CurrencyIndex from ActivityRewards"):
		# doesn't currently account for activity ratings
		if loot_matrix_index is not None:
			loot = loot_matrix.get(loot_matrix_index)
		else:
			loot = None
		if currency_index is not None:
			_, minvalue, maxvalue = currency_table[currency_index][0]
		else:
			minvalue = None
			maxvalue = None

		activity_rewards[object_template] = loot, minvalue, maxvalue

	# actually persistent stuff

	root.item_component = BTrees.IOBTree.BTree()
	for id, base_value, item_type, stack_size, sub_items in cdclient.execute("select id, baseValue, itemType, stackSize, subItems from ItemComponent"):
		if item_type == ItemType.Vehicle:
			stack_size = 1
		if sub_items is None or not sub_items.strip():
			sub_items = ()
		else:
			sub_items = [int(i) for i in sub_items.split(",")]
		root.item_component[id] = base_value, item_type, stack_size, sub_items

	root.item_sets = []
	for item_ids, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in cdclient.execute("select itemIDs, skillSetWith2, skillSetWith3, skillSetWith4, skillSetWith5, skillSetWith6 from ItemSets"):
		item_ids = [int(i) for i in item_ids.split(",")]
		skill_set_2 = []
		if skill_set_with_2 is not None:
			for row in cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i "% skill_set_with_2):
				skill_set_2.append(row[0])
		skill_set_3 = []
		if skill_set_with_3 is not None:
			for row in cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i "% skill_set_with_3):
				skill_set_3.append(row[0])
		skill_set_4 = []
		if skill_set_with_4 is not None:
			for row in cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i "% skill_set_with_4):
				skill_set_4.append(row[0])
		skill_set_5 = []
		if skill_set_with_5 is not None:
			for row in cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i "% skill_set_with_5):
				skill_set_5.append(row[0])
		skill_set_6 = []
		if skill_set_with_6 is not None:
			for row in cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i "% skill_set_with_6):
				skill_set_6.append(row[0])
		root.item_sets.append((item_ids, skill_set_2, skill_set_3, skill_set_4, skill_set_5, skill_set_6))

	root.property_template = BTrees.IOBTree.BTree()
	for map_id, path in cdclient.execute("select mapID, path from PropertyTemplate"):
		float_path = []
		path = path.split()
		coords = [iter(path)] * 3
		for x, y, z in zip(*coords):
			float_path.append((float(x), float(y), float(z)))

		root.property_template[map_id] = tuple(float_path)


	root.script_component = BTrees.IOBTree.BTree()
	root.destructible_component = BTrees.IOBTree.BTree()
	root.vendor_component = BTrees.IOBTree.BTree()
	root.inventory_component = BTrees.IOBTree.BTree()
	root.activities = BTrees.IOBTree.BTree()
	root.rebuild_component = BTrees.IOBTree.BTree()
	root.package_component = BTrees.IOBTree.BTree()
	root.launchpad_component = BTrees.IOBTree.BTree()
	root.mission_npc_component = BTrees.IOBTree.BTree()

	root.components_registry = BTrees.IOBTree.BTree()
	for row in cdclient.execute("select id, component_type, component_id from ComponentsRegistry"):
		root.components_registry.setdefault(row[0], []).append((row[1], row[2]))

		if row[1] == 5 and row[2] not in root.script_component:
			comp_row = cdclient.execute("select id, script_name from ScriptComponent where id == %i" % row[2]).fetchone()
			if comp_row is None:
				continue
			id, script_name = comp_row
			script_name = scripts.SCRIPTS.get(id)
			if script_name is not None:
				root.script_component[id] = script_name

		elif row[1] == 7 and row[2] not in root.destructible_component:
			faction, faction_list, level, loot_matrix_index, currency_index, life, armor, imagination, is_smashable = cdclient.execute("select faction, factionList, level, LootMatrixIndex, CurrencyIndex, life, armor, imagination, isSmashable from DestructibleComponent where id == %i" % row[2]).fetchone()
			if faction is None:
				faction = int(faction_list) # fallback, i have no idea why both columns exist in the first place
			if level is not None and currency_index is not None:
				for npcminlevel, minvalue, maxvalue in reversed(currency_table[currency_index]):
					if npcminlevel < level:
						break
			else:
				minvalue = None
				maxvalue = None
			if loot_matrix_index is not None:
				loot = loot_matrix.get(loot_matrix_index)
			else:
				loot = None

			if life is None:
				life = 1

			if armor is not None:
				armor = int(armor)

			root.destructible_component[row[2]] = faction, (loot, minvalue, maxvalue), life, armor, imagination, is_smashable

		elif row[1] == 16 and row[2] not in root.vendor_component:
			comp_row = cdclient.execute("select LootMatrixIndex from VendorComponent where id == %i" % row[2]).fetchone()
			if comp_row is not None:
				root.vendor_component[row[2]] = loot_matrix.get(comp_row[0])

		elif row[1] == 17 and row[2] not in root.inventory_component:
			for comp_row in cdclient.execute("select itemid, equip from InventoryComponent where id == %i" % row[2]):
				root.inventory_component.setdefault(row[2], []).append((comp_row[0], comp_row[1]))

		elif row[1] == 39 and row[2] not in root.activities:
			for comp_row in cdclient.execute("select instanceMapID from Activities where ActivityID == %i" % row[2]):
				root.activities[row[2]] = comp_row

		elif row[1] == 48 and row[2] not in root.rebuild_component:
			comp_row = cdclient.execute("select complete_time, time_before_smash, reset_time, take_imagination, activityID from RebuildComponent where id == %i" % row[2]).fetchone()
			if comp_row is not None:
				complete_time, smash_time, reset_time, take_imagination, activity_id = comp_row
				if complete_time is None:
					complete_time = 1
				root.rebuild_component[row[2]] = complete_time, smash_time, reset_time, take_imagination, activity_rewards.get(activity_id, (None, None, None))

		elif row[1] == 53 and row[2] not in root.package_component:
			comp_row = cdclient.execute("select LootMatrixIndex from PackageComponent where id == %i" % row[2]).fetchone()
			if comp_row is not None:
				root.package_component[row[2]] = loot_matrix.get(comp_row[0])

		elif row[1] == 67 and row[2] not in root.launchpad_component:
			comp_row = cdclient.execute("select defaultZoneID, targetScene from RocketLaunchpadControlComponent where id == %i " % row[2]).fetchone()
			if comp_row is not None:
				root.launchpad_component[row[2]] = comp_row

		elif row[1] == 73 and row[2] not in root.mission_npc_component:
			root.mission_npc_component[row[2]] = []
			for comp_row in cdclient.execute("select missionID, offersMission, acceptsMission from MissionNPCComponent where id == %i" % row[2]):
				if comp_row[0] in root.missions:
					root.mission_npc_component[row[2]].append(comp_row)

# Create static objects

if GENERATE_WORLD_DATA:
	luz_importer.load_world_data(conn, config["paths"]["client_path"]+"/res/maps")
transaction.commit()
print("Done initializing database!")
