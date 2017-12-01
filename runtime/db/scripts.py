# consider converting all to path so components using the same script are automatically handled
# some paths are removed from the database though

SCRIPTS = {
	40: "general.imagination_powerup_spawner",
	168: "gnarled_forest.campfire",
	313: "general.death_trigger",
	544: "general.flower",
	586: "lego_club.ambient",
	625: "venture_explorer.bob",
	673: "nimbus_station.concert_instrument",
	688: "gnarled_forest.bomb_crate",
	741: "avant_gardens.dusty_holster",
	791: "venture_explorer.imagination_smashable",
	815: "avant_gardens.stromling_mech",
	816: "avant_gardens.turret",
	847: "avant_gardens.rusty_steele",
	849: "nimbus_station.concert_quickbuild",
	867: "avant_gardens.survival.buff_station",
	877: "avant_gardens.caged_spider",
	882: "avant_gardens.survival.world_control",
	901: "avant_gardens.survival.stromling_mech",
	946: "gnarled_forest.torch",
	947: "gnarled_forest.banana_tree",
	952: "general.binoculars",
	973: "lego_club.ambient",
	975: "general.binoculars",
	987: "gnarled_forest.organ",
	992: "nimbus_station.nexus_jay",
	1002: "general.binoculars",
	1021: "general.binoculars",
	1023: "gnarled_forest.jailkeep",
	1054: "general.story_plaque",
	1069: "pet_cove.coalessa",
	1088: "general.mailbox",
	1093: "forbidden_valley.ronin_statue",
	1094: "forbidden_valley.candle",
	1118: "nimbus_station.racetrack.world_control",
	1136: "avant_gardens.property.small.world_control",
	1161: "gnarled_forest.banana_cluster",
	1167: "avant_gardens.wisp_lee",
	1195: "general.wishing_well",
	1206: "forbidden_valley.brickmaster_clang",
	1215: "lego_club.ring",
	1216: "items.cauldron_of_life",
	1218: "items.anvil_of_armor",
	1219: "items.fountain_of_imagination",
	1239: "nimbus_station.lego_club_door",
	1270: "avant_gardens.saluting_npcs",
	1271: "avant_gardens.saluting_npcs",
	1272: "avant_gardens.saluting_npcs",
	1276: "nimbus_station.lup_teleport",
	1329: "crux_prime.aura_blossom_flower",
	1345: "general.poi_mission",
	1349: "crux_prime.scroll_shrine",
	1350: "crux_prime.teapot",
	1419: "nexus_tower.water_fountain",
	1458: "items.sunflower",
	1481: "nexus_tower.vault",
	1484: "nimbus_station.lup_teleport",
	1485: "nimbus_station.lego_club_door",
	1486: "general.transfer_world_on_use",
	1519: "nexus_tower.venture_cannon",
	1527: "general.transfer_world_on_use",
	1556: "nexus_tower.shadow_orb",
	1559: "avant_gardens.property.small.spider_egg",
	1564: "avant_gardens.property.small.spider_queen",
	1566: "avant_gardens.rocco_sirocco",
	1569: "venture_explorer.broken_console",
	1573: "avant_gardens.melodie_foxtrot",
	1581: "avant_gardens.property.small.vance_bulwark",
	1582: "items.maelstrom_vacuum",
	1584: "avant_gardens.monument_bird",
	1586: "avant_gardens.caged_bricks",
	1611: "avant_gardens.epsilon_starcracker",
	1641: "ninjago.ninja",
	1643: "avant_gardens.property.small.dark_spiderling",
	1647: "ninjago.ninja",
	1696: "ninjago.treasure_chest",
	1709: "general.transfer_to_last_non_instance",
	1712: "ninjago.ninja",
	1713: "ninjago.ninja",
	1717: "avant_gardens.laser",
	1718: "avant_gardens.laser",
	1719: "avant_gardens.laser",
	r"02_server\Map\AG\L_AG_LASER_SENSOR_SERVER.lua": "avant_gardens.laser_sensor",
	r"02_server\Map\AM\L_TEMPLE_SKILL_VOLUME.lua": "crux_prime.skill_volume",
	r"02_server\Map\General\L_FORCE_VOLUME_SERVER.lua": "general.force_volume",
	r"02_server\Map\General\L_FRICTION_VOLUME_SERVER.lua": "general.friction_volume",
	r"02_server\Map\General\L_POI_MISSION.lua": "general.poi_mission",
	r"02_server\Map\General\L_TOUCH_MISSION_UPDATE_SERVER.lua": "general.touch_complete_mission",
	r"02_server\Map\NS\L_NS_LUP_TELEPORT.lua": "nimbus_station.lup_teleport",
	r"02_server\Map\NS\L_NS_TOKEN_CONSOLE_SERVER.lua": "nimbus_station.token_console",
	r"02_server\Map\NT\L_NT_ASSEMBLYTUBE_SERVER.lua": "nexus_tower.assembly_tube",
	r"02_server\Map\NT\L_NT_PARADOXTELE_SERVER.lua": "nexus_tower.paradox_teleporter",
	r"02_server\Map\NT\L_NT_SENTINELWALKWAY_SERVER.lua": "nexus_tower.sentinel_speed_pad",
	r"ai\ACT\FootRace\L_ACT_BASE_FOOT_RACE.lua": "general.foot_race",
	r"ai\AG\L_ACT_SHARK_PLAYER_DEATH_TRIGGER.lua": "general.shark_death_trigger",
	r"ai\AG\L_AG_BUS_DOOR.lua": "avant_gardens.moving_bus",
	r"ai\AG\L_AG_FANS.lua": "avant_gardens.fan",
	r"ai\AG\L_AG_JET_EFFECT_SERVER.lua": "avant_gardens.beacon",
	r"ai\AG\L_AG_PICNIC_BLANKET.lua": "avant_gardens.picnic_blanket",
	r"ai\AG\L_AG_QB_Elevator.lua": "avant_gardens.quickbuild_elevator",
	r"ai\AG\L_AG_QB_Wall.lua": "avant_gardens.quickbuild_wall",
	r"ai\AG\L_AG_SHIP_PLAYER_DEATH_TRIGGER.lua": "venture_explorer.death_trigger",
	r"ai\AG\L_AG_SHIP_PLAYER_SHOCK_SERVER.lua": "venture_explorer.broken_console",
	r"ai\AG\L_AG_SHIP_SHAKE.lua": "venture_explorer.ship_shake",
	r"ai\FV\L_ACT_BOUNCE_OVER_WALL.lua": "forbidden_valley.bounce_over_wall",
	r"ai\GF\L_GF_JAIL_WALLS.lua": "gnarled_forest.jail_walls",
	r"ai\GENERAL\L_INSTANCE_EXIT_TRANSFER_PLAYER_TO_LAST_NON_INSTANCE.lua": "general.transfer_to_last_non_instance",
	r"ai\NS\L_NS_CAR_MODULAR_BUILD.lua": "nimbus_station.car_modular_build",
	r"ai\NS\L_NS_JONNY_FLAG_MISSION_SERVER.lua": "nimbus_station.johnny_thunder",
	r"ai\NS\L_NS_MODULAR_BUILD.lua": "nimbus_station.rocket_modular_build",
	r"ai\NS\L_NS_QB_IMAGINATION_STATUE.lua": "nimbus_station.imagination_statue",
	r"ai\NS\NS_PP_01\L_NS_PP_01_TELEPORT.lua": "property.teleport"}

