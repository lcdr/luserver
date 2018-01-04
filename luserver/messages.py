import inspect
import logging
import re
from enum import Enum, IntEnum
from functools import wraps
from typing import Generic, NewType, TypeVar

from pyraknet.bitstream import c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, ReadStream, Serializable
from pyraknet.messages import Address
from .bitstream import WriteStream
from .ldf import LDF

log = logging.getLogger(__name__)

class GeneralMsg(IntEnum):
	@staticmethod
	def header():
		return 0x00

	Handshake = 0x00
	DisconnectNotify = 0x01
	GeneralNotify = 0x02

class AuthServerMsg(IntEnum):
	@staticmethod
	def header():
		return 0x01

	LoginRequest = 0x00

class SocialMsg(IntEnum):
	@staticmethod
	def header():
		return 0x02

	GeneralChatMessage = 0x01
	PrivateChatMessage = 0x02
	AddFriendRequest = 0x07
	AddFriendResponse = 0x08
	RemoveFriend = 0x09
	GetFriendsList = 0x0a
	GetIgnoreList = 0x0d
	TeamInvite = 0x0f
	TeamInviteResponse = 0x10
	TeamGetStatus = 0x15

class WorldServerMsg(IntEnum):
	@staticmethod
	def header():
		return 0x04

	SessionInfo = 0x01
	CharacterListRequest = 0x02
	CharacterCreateRequest = 0x03
	EnterWorld = 0x04 # this is called LoginRequest in the original client, but that's too ambiguous with AuthServerMsg.LoginRequest
	GameMessage = 0x05
	CharacterDeleteRequest = 0x06
	GeneralChatMessage = 0x0e
	LoadComplete = 0x13
	Routing = 0x15
	PositionUpdate = 0x16
	Mail = 0x17
	StringCheck = 0x19

class WorldClientMsg(IntEnum):
	@staticmethod
	def header():
		return 0x05

	LoginResponse = 0x00
	LoadWorld = 0x02
	CharacterData = 0x04
	CharacterList = 0x06
	CharacterCreateResponse = 0x07
	CharacterDeleteResponse = 0x0b
	GameMessage = 0x0c
	Redirect = 0x0e
	BlueprintSaveResponse = 0x15
	AddFriendRequest = 0x1b
	AddFriendResponse = 0x1c
	RemoveFriendResponse = 0x1d
	FriendsList = 0x1e
	TeamInvite = 0x23
	FriendUpdateNotify = 0x1f
	Mail = 0x31
	Moderation = 0x3b

# Sadly no better way to get a mapping from headers to enums
msg_enum = {
	0x00: GeneralMsg,
	0x01: AuthServerMsg,
	0x02: SocialMsg,
	0x04: WorldServerMsg,
	0x05: WorldClientMsg}

class GameMessage(Enum):
	Teleport = 19
	DropClientLoot = 30
	Die = 37
	RequestDie = 38
	PlayEmote = 41
	PlayAnimation = 43
	EchoStartSkill = 118
	StartSkill = 119
	SelectSkill = 124
	AddSkill = 127
	RemoveSkill = 128
	SetCurrency = 133
	PickupCurrency = 137
	PickupItem = 139
	PlayFXEffect = 154
	StopFXEffect = 155
	RequestResurrect = 159
	Resurrect = 160
	PopEquippedItemsState = 192
	Knockback = 202
	RebuildCancel = 209
	EnableRebuild = 213
	MoveItemInInventory = 224
	AddItemToInventoryClientSync = 227
	RemoveItemFromInventory = 230
	EquipInventory = 231
	UnEquipInventory = 233
	OfferMission = 248
	RespondToMission = 249
	NotifyMission = 254
	NotifyMissionTask = 255
	RebuildNotifyState = 336
	TerminateInteraction = 357
	RequestUse = 364
	VendorOpenWindow = 369
	EmotePlayed = 371
	BuyFromVendor = 373
	SellToVendor = 374
	SetInventorySize = 389
	ActivityStart = 407
	VendorStatusUpdate = 417
	ClientItemConsumed = 428
	SetUserCtrlCompPause = 466
	SetFlag = 471
	HasBeenCollected = 486
	PlayerLoaded = 505
	PlayerReady = 509
	RequestLinkedMission = 515
	MissionDialogueOK = 520
	DisplayMessageBox = 529
	MessageBoxRespond = 530
	SetGravityScale = 541
	PlaceModelResponse = 547
	SetJetPackMode = 561
	DisplayTooltip = 569
	UseNonEquipmentItem = 603
	RequestActivitySummaryLeaderboardData = 648
	SendActivitySummaryLeaderboardData = 649
	NotifyPetTamingMinigame = 661
	ClientExitTamingMinigame = 663
	PetTamingMinigameResult = 667
	PetTamingTryBuildResult = 668
	NotifyTamingBuildSuccess = 673
	NotifyPetTamingPuzzleSelected = 675
	SetEmoteLockState = 693
	PlayEmbeddedEffectOnAllClientsNearObject = 713
	DownloadPropertyData = 716
	QueryPropertyData = 717
	NotifyClientZoneObject = 737
	PropertyRentalResponse = 750
	PlayCinematic = 762
	EndCinematic = 763
	CinematicUpdate = 764
	ToggleGhostReferenceOverride = 767
	SetGhostReferencePosition = 768
	FireEventServerSide = 770
	AddCameraEffect = 773
	RemoveAllCameraEffects = 775
	ScriptNetworkVarUpdate = 781
	UpdateModelFromClient = 793
	DeleteModelFromClient = 794
	PlayNDAudioEmitter = 821
	EnterProperty1 = 840
	PropertyEntranceSync = 842
	PropertySelectQuery = 845
	ParseChatMessage = 850
	OpenPropertyVendor = 861
	ClientTradeRequest = 868
	ServerTradeInvite = 870
	ServerTradeInitialReply = 873
	ClientTradeUpdate = 875
	ServerTradeUpdate = 877
	ClientTradeCancel = 878
	ClientTradeAccept = 880
	ServerTradeCancel = 883
	ServerTradeAccept = 884
	ReadyForUpdates = 888
	BounceNotification = 932
	BBBSaveRequest = 1001
	NotifyClientObject = 1042
	DisplayZoneSummary = 1043
	StartBuildingWithItem = 1057
	StartArrangingWithItem = 1061
	FinishArrangingWithItem = 1062
	DoneArrangingWithItem = 1063
	SetBuildMode = 1068
	SetBuildModeConfirmed = 1073
	MoveItemBetweenInventoryTypes = 1093
	ModularBuildMoveAndEquip = 1096
	ModularBuildFinish = 1097
	EchoSyncSkill = 1144
	SyncSkill = 1145
	RequestServerProjectileImpact = 1148
	ModularBuildConvertModel = 1155
	UIMessageServerToSingleClient = 1184
	PetTamingTryBuild = 1197
	ReportBug = 1198
	RequestSmashPlayer = 1202
	FireEventClientSide = 1213
	ToggleGMInvis = 1218
	LockNodeRotation = 1260
	PlayerReachedRespawnCheckpoint = 1296
	HandleUGCEquipPostDeleteBasedOnEditMode = 1300
	HandleUGCEquipPreCreateBasedOnEditMode = 1301
	PropertyContentsFromClient = 1305
	GetModelsOnProperty = 1306
	MatchRequest = 1308
	MatchResponse = 1309
	MatchUpdate = 1310
	ZonePropertyModelRotated = 1370
	ZonePropertyModelRemovedWhileEquipped = 1371
	ZonePropertyModelEquipped = 1372
	NotifyRacingClient = 1390
	RacingPlayerLoaded = 1392
	UsedInformationPlaque = 1419
	ActivateBrickMode = 1438
	ModifyLegoScore = 1459
	RestoreToPostLoadStats = 1468
	SetRailMovement = 1471
	StartRailMovement = 1472
	ClientRailMovementReady = 1476
	GetHotPropertyData = 1511
	PropertyEntranceBegin = 1553
	FreezeAnimation = 1579
	StartCelebrationEffect = 1618
	ServerDoneLoadingAllObjects = 1642
	ForceCameraTargetCycle = 1678
	NotifyServerLevelProcessingComplete = 1734
	NotifyLevelRewards = 1735

ObjectID = NewType("ObjectID", int)

# todo: change to UnsignedIntStruct
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

class Sequence(Generic[T, U]):
	pass

class Mapping(Generic[T, U, V]):
	pass

def _send_game_message(mode):
	"""
	Send a game message on calling its function.
	Modes:
		broadcast: The game message will be sent to all connected players. If "player" is specified, that player will be excluded.
		single: The game message will only be sent to the player this game message belongs to. If the object is not a player, specify "player" explicitly.
	The serialization is handled as follows:
		The Game Message ID is taken from the function name.
		The argument serialization order is taken from the function definition.
		Any arguments with defaults (a default of None is ignored)(also according to the function definition) will be wrapped in a flag and only serialized if the argument is not the default.
		The serialization type (c_int, c_float, etc) is taken from the argument annotation.

	If the function has "player" as the first argument, the player that this message will be sent to will be passed to the function as that argument. Note that this only really makes sense to specify in "single" mode.
	"""
	def decorator(func):
		from .world import server

		@wraps(func)
		def wrapper(self, *args, **kwargs):
			game_message_id = GameMessage[re.sub("(^|_)(.)", lambda match: match.group(2).upper(), func.__name__)].value
			out = WriteStream()
			out.write_header(WorldClientMsg.GameMessage)
			object_id = self.object.object_id
			out.write(c_int64(object_id))
			out.write(c_ushort(game_message_id))

			signature = inspect.signature(func)
			params = list(signature.parameters.values())[1:]

			if "player" in kwargs:
				player = kwargs["player"]
			else:
				player = None
			if params and params[0].name == "player":
				params.pop(0)
			else:
				if "player" in kwargs:
					del kwargs["player"]

			bound_args = signature.bind(self, *args, **kwargs)
			for param in params:
				if param.annotation == bool:
					if param.name in bound_args.arguments:
						value = bound_args.arguments[param.name]
					else:
						value = param.default
					assert value in (True, False)
					out.write(c_bit(value))
				else:
					if param.default not in (param.empty, None):
						is_not_default = param.name in bound_args.arguments and bound_args.arguments[param.name] != param.default
						out.write(c_bit(is_not_default))
						if not is_not_default:
							continue

					if param.name not in bound_args.arguments:
						raise TypeError("\"%s\" needs to be specified" % param.name)
					value = bound_args.arguments[param.name]
					_game_message_serialize(out, param.annotation, value)
			if mode == "broadcast":
				exclude_address = None
				if player is not None:
					exclude_address = player.char.address
				server.send(out, address=exclude_address, broadcast=True)
			elif mode == "single":
				if player is None:
					player = self.object
				server.send(out, address=player.char.address)
			if func.__name__ not in ("drop_client_loot", "script_network_var_update"): # todo: don't hardcode this
				if len(bound_args.arguments) > 1:
					log.debug(", ".join("%s=%s" % (key, value) for key, value in list(bound_args.arguments.items())[1:]))
			return func(self, *args, **kwargs)
		return wrapper
	return decorator

broadcast = _send_game_message("broadcast")
single = _send_game_message("single")

def _game_message_serialize(out, type, value):
	from .game_object import GameObject
	if type == float:
		out.write(c_float(value))
	elif type == bytes:
		out.write(c_uint(len(value)))
		out.write(value)
	elif type == str:
		out.write(value, length_type=c_uint)
	elif type in (c_int, c_int64, c_ubyte, c_uint, c_uint64):
		out.write(type(value))
	elif type == ReadStream:
		out.write(c_uint(len(value)))
		out.write(bytes(value))
	elif type == LDF:
		ldf_text = value.to_str()
		out.write(ldf_text, length_type=c_uint)
		if ldf_text:
			out.write(bytes(2)) # for some reason has a null terminator
	elif type == GameObject:
		if value is None:
			out.write(c_int64(0))
		else:
			out.write(c_int64(value.object_id))
	elif inspect.isclass(type) and issubclass(type, Serializable):
		type.serialize(value, out)
	elif issubclass(type, Sequence):
		length_type, value_type = type.__args__
		out.write(length_type(len(value)))
		for i in value:
			_game_message_serialize(out, value_type, i)
	elif issubclass(type, Mapping):
		length_type, key_type, value_type = type.__args__
		out.write(length_type(len(value)))
		for k, v in value.items():
			_game_message_serialize(out, key_type, k)
			_game_message_serialize(out, value_type, v)
		else:
			raise ValueError(type)
	else:
		raise TypeError(type)

def game_message_deserialize(message, type):
	from .game_object import GameObject
	from .world import server
	if type == float:
		return message.read(c_float)
	if type == bytes:
		return message.read(bytes, length=message.read(c_uint))
	if type == str:
		return message.read(str, length_type=c_uint)
	if type in (c_int, c_int64, c_ubyte, c_uint, c_uint64):
		return message.read(type)
	if type == ReadStream:
		length = message.read(c_uint)
		return ReadStream(message.read(bytes, length=length))
	if type == LDF:
		value = message.read(str, length_type=c_uint)
		if value:
			assert message.read(c_ushort) == 0 # for some reason has a null terminator
		# todo: convert to LDF
		return value
	if type == GameObject:
		return server.get_object(message.read(c_int64))
	if inspect.isclass(type) and issubclass(type, Serializable):
		return type.deserialize(message)
	if issubclass(type, Sequence):
		length_type, value_type = type.__args__
		value = []
		for _ in range(game_message_deserialize(message, length_type)):
			value.append(game_message_deserialize(message, value_type))
		return value
	if issubclass(type, Mapping):
		length_type, key_type, value_type = type.__args__
		value = {}
		for _ in range(game_message_deserialize(message, length_type)):
			key = game_message_deserialize(message, key_type)
			val = game_message_deserialize(message, value_type)
			value[key] = val
		return value
	raise TypeError(type)
