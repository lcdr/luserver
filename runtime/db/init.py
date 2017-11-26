import os
import sqlite3
import subprocess
import time

import BTrees
import toml
import transaction
import ZEO
from persistent.mapping import PersistentMapping

from luserver.auth import Account, GMLevel
from luserver.world import World
from luserver.components.inventory import ItemType
from luserver.components.mission import TaskType

import init_skills
import luz_importer
import scripts

class Init:
	def __init__(self, gen_accounts, gen_config, gen_skills, gen_missions, gen_comps, gen_world):
		config_dir = os.path.normpath(os.path.join(__file__, ".."))
		with open(os.path.join(config_dir, "db.toml"), encoding="utf8") as file:
			self.config = toml.load(file)
		self.config["paths"]["cdclient_path"] = os.path.normpath(os.path.join(config_dir, self.config["paths"]["cdclient_path"]))
		self.config["paths"]["client_path"] = os.path.normpath(os.path.join(config_dir, self.config["paths"]["client_path"]))

		while True:
			try:
				conn = ZEO.connection(12345, wait_timeout=3)
				break
			except ZEO.Exceptions.ClientDisconnected:
				if os.name == "nt":
					flags = subprocess.CREATE_NEW_CONSOLE
				else:
					flags = 0
				subprocess.Popen("runzeo -a 12345 -f " + os.path.normpath(os.path.join(__file__, "..", "server_db.db")), shell=True, creationflags=flags)
				time.sleep(3)

		self.root = conn.root
		self.cdclient = sqlite3.connect(self.config["paths"]["cdclient_path"])

		if gen_accounts:
			self.gen_accounts()
		if gen_config:
			self.gen_config()
		if gen_skills:
			init_skills.Init(self.root, self.cdclient)
		if gen_missions:
			self.gen_missions()
		if gen_comps:
			self.gen_comps()
		if gen_world:
			luz_importer.import_data(self.root, os.path.join(self.config["paths"]["client_path"], "res", "maps"))

		transaction.commit()
		print("Done initializing database!")

	def gen_accounts(self):
		self.root.current_instance_id = 0
		self.root.current_clone_id = 1
		self.root.accounts = BTrees.OOBTree.BTree()
		admin_username = input("Enter admin username: ")
		while True:
			admin_password = input("Enter admin password: ")
			if len(admin_password) < 10:
				print("Password too short, min 10 chars")
			else:
				break
		self.root.accounts[admin_username] = Account(admin_username, admin_password)
		self.root.accounts[admin_username].gm_level = GMLevel.Admin

		self.root.servers = BTrees.OOBTree.BTree()

		self.root.properties = BTrees.IOBTree.BTree()
		for world in (World.BlockYard, World.AvantGrove, World.NimbusRock, World.NimbusIsle, World.ChanteyShanty, World.RavenBluff):
			self.root.properties[world.value] = BTrees.OOBTree.BTree()

		# Read-only data
		# All "tables" below don't need things like PersistentList instead of normal list, since they will never be modified

		self.root.predef_names = []
		for name_part in ("first", "middle", "last"):
			names = []
			with open(os.path.join(self.config["paths"]["client_path"], "res", "names", "minifigname_"+name_part+".txt")) as file:
				for name in file:
					names.append(name[:-1])

			self.root.predef_names.append(names)

		self.root.colors = BTrees.IOBTree.BTree()
		for row in self.cdclient.execute("select id, validCharacters from BrickColors"):
			self.root.colors[row[0]] = bool(row[1])

		self.root.level_scores = tuple(i[0] for i in self.cdclient.execute("select requiredUScore from LevelProgressionLookup").fetchall())

		self.root.world_info = BTrees.IOBTree.BTree()
		for world_id, script_id, template in self.cdclient.execute("select zoneID, scriptID, zoneControlTemplate from ZoneTable"):
			self.root.world_info[world_id] = scripts.SCRIPTS.get(script_id), template

	def gen_config(self):
		self.root.config = PersistentMapping()
		self.root.config["auth_enabled"] = True
		self.root.config["credits"] = "Created by lcdr"
		for entry in self.config["defaults"]:
			self.root.config[entry] = self.config["defaults"][entry]

	def gen_missions(self):
		self.root.missions = BTrees.IOBTree.BTree()
		for id, prereq, currency, universe_score, is_choice_reward, reward_item1, reward_item1_count, reward_item2, reward_item2_count, reward_item3, reward_item3_count, reward_item4, reward_item4_count, reward_emote, reward_max_imagination, reward_max_life, reward_max_items, is_mission, is_random, random_pool in self.cdclient.execute("select id, prereqMissionID, reward_currency, LegoScore, isChoiceReward, reward_item1, reward_item1_count, reward_item2, reward_item2_count, reward_item3, reward_item3_count, reward_item4, reward_item4_count, reward_emote, reward_maximagination, reward_maxhealth, reward_maxinventory, isMission, isRandom, randomPool from Missions"):
			# prereqs
			prereqs = []
			if prereq:
				prereq = prereq.replace("(", "").replace(")", "").replace("&", ",") # normalize pointless syntax
				for i in prereq.split(","):
					prereq_ors = i.split("|")
					prereqs.append(tuple(tuple(int(k) for k in j.split(":")) if ":" in j else int(j) for j in prereq_ors)) # : in prereqs is mission state

			# tasks
			tasks = []
			for task_type, target, target_group, target_value, parameter in self.cdclient.execute("select taskType, target, targetGroup, targetValue, taskParam1 from MissionTasks where id = "+str(id)):
				if task_type in (TaskType.KillEnemy, TaskType.Script, TaskType.QuickBuild, TaskType.ObtainItem, TaskType.MissionComplete, TaskType.CollectPowerup, TaskType.TamePet):
					target = target,
					if target_group:
						target += tuple(int(target_id) for target_id in target_group.split(","))
				elif task_type in (TaskType.UseEmote, TaskType.UseSkill):
					parameter = tuple(int(param_id) for param_id in parameter.split(","))
				elif task_type == TaskType.Discover:
					target = target_group
				elif task_type == TaskType.MinigameAchievement:
					parameter = target_group
				elif task_type == TaskType.Flag:
					target = tuple(int(flag_id) for flag_id in target_group.split(","))
				if task_type == TaskType.ObtainItem:
					if not parameter:
						parameter = None
					else:
						parameter = int(parameter)

				tasks.append((task_type, target, target_value, parameter))

			reward_items = []
			for lot, count in ((reward_item1, reward_item1_count), (reward_item2, reward_item2_count), (reward_item3, reward_item3_count), (reward_item4, reward_item4_count)):
				if lot != -1:
					if count == 0:
						count = 1
					reward_items.append((lot, count))

			if reward_emote == -1:
				reward_emote = None

			if not is_mission:
				# achievements don't have choices, this is inconsistent in the DB
				is_choice_reward = False

			if not random_pool:
				random_pool = None
			else:
				random_pool = tuple(int(mission_id) for mission_id in random_pool.split(","))

			self.root.missions[id] = (currency, universe_score, bool(is_choice_reward), tuple(reward_items), reward_emote, reward_max_life, reward_max_imagination, reward_max_items), tuple(prereqs), tuple(tasks), bool(is_mission), bool(is_random), random_pool

		self.root.mission_mail = BTrees.IOBTree.BTree()
		for id, mission_id, attachment_lot in self.cdclient.execute("select ID, missionID, attachmentLOT from MissionEmail where attachmentLOT is not null"):
			if attachment_lot == 0:
				attachment_lot = None
			self.root.mission_mail.setdefault(mission_id, []).append((id, attachment_lot))

		# i guess this fits in best with missions

		self.root.level_rewards = BTrees.IOBTree.BTree()
		for level, reward_type, value in self.cdclient.execute("select LevelID, RewardType, value from Rewards"):
			self.root.level_rewards.setdefault(level, []).append((reward_type, value))

	def gen_comps(self):
		# temporary, not actually needed for the server (therefore dict instead of root assignment)
		currency_table = {}
		for row in self.cdclient.execute("select currencyIndex, npcminlevel, minvalue, maxvalue from CurrencyTable"):
			currency_table.setdefault(row[0], []).append((row[1], row[2], row[3]))

		loot_matrix = {}
		self.root.loot_table = BTrees.IOBTree.BTree()
		for matrix_index, table_index, percent, min_drop, max_drop in self.cdclient.execute("select LootMatrixIndex, LootTableIndex, percent, minToDrop, maxToDrop from LootMatrix"):
			if table_index not in self.root.loot_table:
				loot_table_entry = []
				for loot_table_row in self.cdclient.execute("select itemid, MissionDrop, sortPriority from LootTable where LootTableIndex == %i" % table_index):
					loot_table_entry.append(loot_table_row)
				self.root.loot_table[table_index] = tuple(loot_table_entry)
			loot_matrix.setdefault(matrix_index, []).append((table_index, percent, min_drop, max_drop))

		# actually persistent stuff

		self.root.activity_rewards = BTrees.IOBTree.BTree()
		for object_template, loot_matrix_index, currency_index in self.cdclient.execute("select objectTemplate, LootMatrixIndex, CurrencyIndex from ActivityRewards"):
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

			self.root.activity_rewards[object_template] = loot, minvalue, maxvalue



		item_type_fixes = {
			3513: ItemType.RightHand,  # NPC Sky Lane Helmet
			3514: ItemType.Neck,  # NPC Sky Lane ShoulderPads
			3515: ItemType.Hat,  # NPC Sky Lane Hair
			3517: ItemType.Hat,  # NPC Epsilon Starcracker Helmet
			3519: ItemType.Neck,  # NPC Epsilon Starcracker Rocketpack
			3534: ItemType.Hat,  # NPC Melodie Foxtrot Hair
			3565: ItemType.Hat,  # Test Samurai KIT Helmet
			3570: ItemType.Hat,  # Test Will_L kit Helmet
			3809: ItemType.Hat,  # NPC Mardolf Hat
			3811: ItemType.Hat,  # NPC Johnny Thunder Hat
			3814: ItemType.Hat,  # NPC Numbchuck Helmet
			3815: ItemType.Hat,  # NPC Coalessa Hair
		}

		self.root.item_component = BTrees.IOBTree.BTree()
		for id, base_value, item_type, stack_size, sub_items in self.cdclient.execute("select id, baseValue, itemType, stackSize, subItems from ItemComponent"):
			if id in item_type_fixes:
				item_type = item_type_fixes[id]
			if sub_items is None or not sub_items.strip():
				sub_items = ()
			else:
				sub_items = [int(i) for i in sub_items.split(",")]
			self.root.item_component[id] = base_value, item_type, stack_size, sub_items

		self.root.item_sets = []
		for item_ids, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in self.cdclient.execute("select itemIDs, skillSetWith2, skillSetWith3, skillSetWith4, skillSetWith5, skillSetWith6 from ItemSets"):
			item_ids = [int(i) for i in item_ids.split(",")]
			skill_set_2 = []
			if skill_set_with_2 is not None:
				for row in self.cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i " % skill_set_with_2):
					skill_set_2.append(row[0])
			skill_set_3 = []
			if skill_set_with_3 is not None:
				for row in self.cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i " % skill_set_with_3):
					skill_set_3.append(row[0])
			skill_set_4 = []
			if skill_set_with_4 is not None:
				for row in self.cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i " % skill_set_with_4):
					skill_set_4.append(row[0])
			skill_set_5 = []
			if skill_set_with_5 is not None:
				for row in self.cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i " % skill_set_with_5):
					skill_set_5.append(row[0])
			skill_set_6 = []
			if skill_set_with_6 is not None:
				for row in self.cdclient.execute("select SkillID from ItemSetSkills where SkillSetID ==  %i " % skill_set_with_6):
					skill_set_6.append(row[0])
			self.root.item_sets.append((item_ids, skill_set_2, skill_set_3, skill_set_4, skill_set_5, skill_set_6))

		self.root.property_template = BTrees.IOBTree.BTree()
		for map_id, path in self.cdclient.execute("select mapID, path from PropertyTemplate"):
			float_path = []
			path = path.split()
			coords = [iter(path)] * 3
			for x, y, z in zip(*coords):
				float_path.append((float(x), float(y), float(z)))

			self.root.property_template[map_id] = tuple(float_path)


		self.root.script_component = BTrees.IOBTree.BTree()
		self.root.destructible_component = BTrees.IOBTree.BTree()
		self.root.vendor_component = BTrees.IOBTree.BTree()
		self.root.inventory_component = BTrees.IOBTree.BTree()
		self.root.activities = BTrees.IOBTree.BTree()
		self.root.rebuild_component = BTrees.IOBTree.BTree()
		self.root.package_component = BTrees.IOBTree.BTree()
		self.root.launchpad_component = BTrees.IOBTree.BTree()
		self.root.mission_npc_component = BTrees.IOBTree.BTree()

		self.root.components_registry = BTrees.IOBTree.BTree()
		for row in self.cdclient.execute("select id, component_type, component_id from ComponentsRegistry"):
			self.root.components_registry.setdefault(row[0], []).append((row[1], row[2]))

			if row[1] == 5 and row[2] not in self.root.script_component:
				# we don't even need to query the db since we've got our own scripts table
				script_id = row[2]
				if script_id in scripts.SCRIPTS:
					self.root.script_component[script_id] = scripts.SCRIPTS[script_id]

			elif row[1] == 7 and row[2] not in self.root.destructible_component:
				faction, faction_list, level, loot_matrix_index, currency_index, life, armor, imagination, is_smashable = self.cdclient.execute("select faction, factionList, level, LootMatrixIndex, CurrencyIndex, life, armor, imagination, isSmashable from DestructibleComponent where id == %i" % row[2]).fetchone()
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

				if life is None or life < 1:
					life = 1

				if armor is not None:
					armor = int(armor)

				self.root.destructible_component[row[2]] = faction, (loot, minvalue, maxvalue), life, armor, imagination, is_smashable

			elif row[1] == 16 and row[2] not in self.root.vendor_component:
				comp_row = self.cdclient.execute("select LootMatrixIndex from VendorComponent where id == %i" % row[2]).fetchone()
				if comp_row is not None:
					self.root.vendor_component[row[2]] = loot_matrix.get(comp_row[0])

			elif row[1] == 17 and row[2] not in self.root.inventory_component:
				for comp_row in self.cdclient.execute("select itemid, equip from InventoryComponent where id == %i" % row[2]):
					self.root.inventory_component.setdefault(row[2], []).append((comp_row[0], comp_row[1]))

			elif row[1] == 39 and row[2] not in self.root.activities:
				for comp_row in self.cdclient.execute("select instanceMapID from Activities where ActivityID == %i" % row[2]):
					self.root.activities[row[2]] = comp_row

			elif row[1] == 48 and row[2] not in self.root.rebuild_component:
				comp_row = self.cdclient.execute("select complete_time, time_before_smash, reset_time, take_imagination, activityID from RebuildComponent where id == %i" % row[2]).fetchone()
				if comp_row is not None:
					complete_time, smash_time, reset_time, take_imagination, activity_id = comp_row
					if complete_time is None:
						complete_time = 1
					self.root.rebuild_component[row[2]] = complete_time, smash_time, reset_time, take_imagination, activity_id

			elif row[1] == 53 and row[2] not in self.root.package_component:
				comp_row = self.cdclient.execute("select LootMatrixIndex from PackageComponent where id == %i" % row[2]).fetchone()
				if comp_row is not None:
					self.root.package_component[row[2]] = loot_matrix.get(comp_row[0])

			elif row[1] == 67 and row[2] not in self.root.launchpad_component:
				comp_row = self.cdclient.execute("select targetZone, defaultZoneID, targetScene from RocketLaunchpadControlComponent where id == %i " % row[2]).fetchone()
				if comp_row is not None:
					self.root.launchpad_component[row[2]] = comp_row

			elif row[1] == 73 and row[2] not in self.root.mission_npc_component:
				self.root.mission_npc_component[row[2]] = []
				for comp_row in self.cdclient.execute("select missionID, offersMission, acceptsMission from MissionNPCComponent where id == %i" % row[2]):
					if comp_row[0] in self.root.missions:
						self.root.mission_npc_component[row[2]].append(comp_row)

if __name__ == "__main__":
	# temporarily using int instead of bool for faster editing
	GENERATE_ACCOUNTS = 1
	GENERATE_CONFIG = 1
	GENERATE_SKILLS = 1
	GENERATE_MISSIONS = 1
	GENERATE_COMPS = 1
	GENERATE_WORLD_DATA = 1
	Init(GENERATE_ACCOUNTS, GENERATE_CONFIG, GENERATE_SKILLS, GENERATE_MISSIONS, GENERATE_COMPS, GENERATE_WORLD_DATA)
