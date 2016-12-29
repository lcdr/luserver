import inspect
import logging
import re
from enum import Enum, IntEnum
from functools import wraps

from pyraknet.messages import Message
from . import amf3
from .bitstream import BitStream, c_bit, c_float, c_int64, c_uint, c_ushort
from .ldf import LDF
from .math.vector import Vector3
from .math.quaternion import Quaternion

log = logging.getLogger(__name__)

Message.LUPacket = 0x53

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
msg_enum = {}
msg_enum[0x00] = GeneralMsg
msg_enum[0x01] = AuthServerMsg
msg_enum[0x02] = SocialMsg
msg_enum[0x04] = WorldServerMsg
msg_enum[0x05] = WorldClientMsg

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
	SetFlag = 471
	HasBeenCollected = 486
	PlayerLoaded = 505
	PlayerReady = 509
	RequestLinkedMission = 515
	MissionDialogueOK = 520
	DisplayMessageBox = 529
	MessageBoxRespond = 530
	PlaceModelResponse = 547
	SetJetPackMode = 561
	DisplayTooltip = 569
	UseNonEquipmentItem = 603
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
	PropertyRentalResponse = 750
	ToggleGhostReferenceOverride = 767
	SetGhostReferencePosition = 768
	FireEventServerSide = 770
	ScriptNetworkVarUpdate = 781
	UpdateModelFromClient = 793
	DeleteModelFromClient = 794
	PlayNDAudioEmitter = 821
	EnterProperty1 = 840
	PropertyEntranceSync = 842
	PropertySelectQuery = 845
	ParseChatMessage = 850
	OpenPropertyVendor = 861
	ReadyForUpdates = 888
	BounceNotification = 932
	BBBSaveRequest = 1001
	NotifyClientObject = 1042
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
	HandleUGCEquipPostDeleteBasedOnEditMode = 1300
	PropertyContentsFromClient = 1305
	GetModelsOnProperty = 1306
	MatchRequest = 1308
	MatchResponse = 1309
	MatchUpdate = 1310
	UsedInformationPlaque = 1419
	ActivateBrickMode = 1438
	ModifyLegoScore = 1459
	RestoreToPostLoadStats = 1468
	SetRailMovement = 1471
	StartRailMovement = 1472
	ClientRailMovementReady = 1476
	GetHotPropertyData = 1511
	PropertyEntranceBegin = 1553
	StartCelebrationEffect = 1618
	ServerDoneLoadingAllObjects = 1642
	NotifyServerLevelProcessingComplete = 1734

def send_game_message(mode):
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

	If there are some cases where you don't want to send a game message but only call the serverside function, specify send=False.
	If the function has "player" as the first argument, the player that this message will be sent to will be passed to the function as that argument. Note that this only really makes sense to specify in "single" mode.
	"""
	def decorator(func):
		@wraps(func)
		def wrapper(self, *args, send=True, **kwargs):
			if send:
				game_message_id = GameMessage[re.sub("(^|_)(.)", lambda match: match.group(2).upper(), func.__name__)].value
				out = BitStream()
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
					if param.annotation == c_bit:
						if param.name in bound_args.arguments:
							value = bound_args.arguments[param.name]
						else:
							value = param.default
						assert value in (True, False)
						out.write(param.annotation(value))
					else:
						if param.default not in (param.empty, None):
							is_not_default = param.name in bound_args.arguments and bound_args.arguments[param.name] != param.default
							out.write(c_bit(is_not_default))
							if not is_not_default:
								continue

						value = bound_args.arguments[param.name]
						assert value is not None, "\"%s\" needs to be specified" % param.name
						game_message_serialize(out, param.annotation, value)
				if mode == "broadcast":
					exclude_address = None
					if player is not None:
						exclude_address = player.char.address
					self.object._v_server.send(out, address=exclude_address, broadcast=True)
				elif mode == "single":
					if player is None:
						player = self.object
					self.object._v_server.send(out, address=player.char.address)
				if func.__name__ != "drop_client_loot": # todo: don't hardcode this
					if args or kwargs:
						log.debug(", ".join(str(i) for i in args)+", ".join("%s=%s" % (key, value) for key, value in kwargs.items()))
			return func(self, *args, **kwargs)
		return wrapper
	return decorator

broadcast = send_game_message("broadcast")
single = send_game_message("single")

from .components.property import PropertyData, PropertySelectQueryProperty

def game_message_serialize(out, type, value):
	if isinstance(type, tuple):
		out.write(type[0](len(value)))
		if len(type) == 2: # list
			for i in value:
				game_message_serialize(out, type[1], i)
		elif len(type) == 3: # dict
			for k, v in value.items():
				game_message_serialize(out, type[1], k)
				game_message_serialize(out, type[2], v)

	elif type == Vector3:
		out.write(c_float(value.x))
		out.write(c_float(value.y))
		out.write(c_float(value.z))
	elif type == Quaternion:
		out.write(c_float(value.x))
		out.write(c_float(value.y))
		out.write(c_float(value.z))
		out.write(c_float(value.w))
	elif type in (PropertyData, PropertySelectQueryProperty):
		value.serialize(out)
	elif type == BitStream:
		out.write(c_uint(len(value)))
		out.write(bytes(value))
	elif type == LDF:
		ldf_text = value.to_str()
		out.write(ldf_text, length_type=c_uint)
		if ldf_text:
			out.write(bytes(2)) # for some reason has a null terminator
	elif type == "amf":
		amf3.write(value, out)
	elif type == "str":
		out.write(value, char_size=1, length_type=c_uint)
	elif type == "wstr":
		out.write(value, char_size=2, length_type=c_uint)
	else:
		out.write(type(value))

def game_message_deserialize(message, type):
	if isinstance(type, tuple):
		if len(type) == 2: # list
			value = []
			for _ in range(game_message_deserialize(message, type[0])):
				value.append(game_message_deserialize(message, type[1]))
		elif len(type) == 3: # dict
			value = {}
			for _ in range(game_message_deserialize(message, type[0])):
				value[game_message_deserialize(message, type[1])] = game_message_deserialize(message, type[2])
		return value

	if type == Vector3:
		return Vector3(message.read(c_float), message.read(c_float), message.read(c_float))
	if type == Quaternion:
		return Quaternion(message.read(c_float), message.read(c_float), message.read(c_float), message.read(c_float))
	if type == PropertyData:
		value = PropertyData()
		value.deserialize(message)
		return value
	if type == PropertySelectQueryProperty:
		value = PropertySelectQueryProperty()
		value.deserialize(message)
		return value
	if type == BitStream:
		length = message.read(c_uint)
		return BitStream(message.read(bytes, length=length))
	if type == LDF:
		value = message.read(str, length_type=c_uint)
		if value:
			assert message.read(c_ushort) == 0 # for some reason has a null terminator
		# todo: convert to LDF
		return value
	if type == "amf":
		return amf3.read(message)
	if type == "str":
		return message.read(str, char_size=1, length_type=c_uint)
	if type == "wstr":
		return message.read(str, char_size=2, length_type=c_uint)

	return message.read(type)
