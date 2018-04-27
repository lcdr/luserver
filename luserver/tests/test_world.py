from unittest.mock import Mock, patch

from luserver.world import BITS_LOCAL, BITS_PERSISTENT, BITS_SPAWNED, Event, WorldServer

import pyraknet.server
from luserver.auth import Account
from luserver.bitstream import WriteStream
from luserver.game_object import Player
from luserver.messages import WorldServerMsg
from luserver.tests.test_server import ServerTest

class WorldTest(ServerTest):
	SESSION_KEY = "session key"

	def set_up_db(self):
		super().set_up_db()
		self.db.components_registry = {1: [(1, 1), (2, 0), (4, 0), (7, 4), (9, 0), (17, 0), (55, 0), (68, 0), (107, 0)], 2365: [(50, 0)], 1858: [(2, 1735), (3, 1046), (7, 811)]}
		self.db.config = {"enabled_worlds": ()}
		self.db.current_instance_id = 0
		self.db.current_clone_id = 0
		self.db.destructible_component = {4: (1, (None, None, None), 4, 0, 0, 0), 811: (6, (None, None, None), 1, 0, 0, 1)}
		self.db.inventory_component = {}
		self.db.object_skills = {}
		p = Mock()
		p.__getitem__ = lambda *args: {}
		self.db.properties = p
		self.db.missions = {}
		self.db.servers = {}
		self.db.world_info = {1000: (None, None)}

		world_data = Mock()
		world_data.objects = {}
		self.db.world_data = {1000: world_data}

	def set_up_server(self):
		with patch("luserver.world.WorldServer._load_plugins"):
			return WorldServer(("localhost", 12345), "localhost", (1000, 0), 10, self.conn)

	def send_session_info(self, session_key=SESSION_KEY):
		session_info = WriteStream()
		session_info.write_header(WorldServerMsg.SessionInfo)
		session_info.write(self.USERNAME, allocated_length=33)
		session_info.write(session_key, allocated_length=33)
		self.server._on_lu_packet(bytes(session_info), self.ADDRESS)

class NoAccountWorldTest(WorldTest):
	def setUp(self):
		super().setUp()
		self.handler = Mock()

	def test_session_info_no_user(self):
		self.send_session_info()
		self.server._server.close_connection.assert_called_once_with(self.ADDRESS)

	def test_add_handler(self):
		self.server.add_handler(Event.Spawn, self.handler)
		self.server.handle(Event.Spawn)
		self.handler.assert_called_once_with()

	def test_remove_handler(self):
		self.test_add_handler()
		self.handler.reset_mock()
		self.server.remove_handler(Event.Spawn, self.handler)
		self.server.handle(Event.Spawn)
		self.handler.assert_not_called()

	def test_remove_nonexisting_handler(self):
		with self.assertRaises(RuntimeError):
			self.server.remove_handler(Event.Spawn, self.handler)

	def test_new_id(self):
		self.assertTrue(self.server.new_object_id() | BITS_PERSISTENT)
		self.assertTrue(self.server.new_spawned_id() | BITS_SPAWNED)

	def test_get_zero_object(self):
		with self.assertRaises(ValueError):
			self.server.get_object(0)

	def test_get_nonexisting_object(self):
		with self.assertRaises(KeyError):
			self.server.get_object(12345)

	def test_get_object(self):
		obj = self.server.spawn_object(1858)
		get_obj = self.server.get_object(obj.object_id)
		self.assertIs(get_obj, obj)

	def test_get_objs_in_group(self):
		objs = []
		self.server.spawn_object(1858)
		self.server.spawn_object(1858, {"groups": ()})
		objs.append(self.server.spawn_object(1858, {"groups": ("test",)}))
		objs.append(self.server.spawn_object(1858, {"groups": ("test", "other")}))
		self.server.spawn_object(1858)
		get_objs = self.server.get_objects_in_group("test")
		self.assertEqual(get_objs, objs)

class ExistingAccountWorldTest(WorldTest):
	CHAR_NAME = "char"

	def setUp(self):
		super().setUp()
		self.db.accounts[self.USERNAME] = Account(self.USERNAME, self.PASSWORD)
		self.db.accounts[self.USERNAME].session_key = self.SESSION_KEY
		self.db.accounts[self.USERNAME].selected_char_name = self.CHAR_NAME
		self.player = self.db.accounts[self.USERNAME].characters[self.CHAR_NAME] = Player(123 | BITS_PERSISTENT)
		self.player.name = self.CHAR_NAME
		self.player.char.account = self.db.accounts[self.USERNAME]

class NoSessionWorldTest(ExistingAccountWorldTest):
	def test_session_info_existing_user(self):
		mock = Mock()
		with patch("luserver.modules.general.GeneralHandling.on_validated", mock):
			self.send_session_info()
			mock.assert_called_once_with(self.ADDRESS)

	def test_session_info_incorrect_session_key(self):
		self.send_session_info("incorrect")
		self.server._server.close_connection.assert_called_once_with(self.ADDRESS)

	def test_find_no_player_by_name(self):
		with self.assertRaises(KeyError):
			self.server.find_player_by_name("nonexisting")

	def test_find_player_by_name(self):
		self.assertIs(self.server.find_player_by_name(self.CHAR_NAME), self.db.accounts[self.USERNAME].characters[self.CHAR_NAME])

class SessionWorldTest(ExistingAccountWorldTest):
	def setUp(self):
		super().setUp()
		self.send_session_info()
		self.server._server.send.reset_mock()

class DisconnectTest(SessionWorldTest):
	def test_disconnect(self):
		self.server._server._handle(pyraknet.server.Event.Disconnect, self.ADDRESS)
		self.assertNotIn(self.ADDRESS, self.server.accounts)

