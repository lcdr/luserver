from enum import Enum, IntEnum

from pyraknet.messages import Message

Message.LUPacket = 0x53

# for the enums below, __int__() returns the corresponding header

class GeneralMsg(IntEnum):
	@staticmethod
	def __int__():
		return 0x00

	Handshake = 0x00
	DisconnectNotify = 0x01
	GeneralNotify = 0x02

class AuthServerMsg(IntEnum):
	@staticmethod
	def __int__():
		return 0x01

	LoginRequest = 0x00

class SocialMsg(IntEnum):
	@staticmethod
	def __int__():
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
	def __int__():
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
	def __int__():
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
	Die	= 37
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
	VendorStatusUpdate = 417
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
