from pyraknet.bitstream import c_int, c_int64
from ...ldf import LDF, LDFDataType
from ...messages import single

class MatchRequestType:
	Join = 0
	Ready = 1

class MatchRequestValue:
	Leave = 0
	Ready = 1
	Join = 5

class MatchUpdateType:
	Time = 3

class CharActivity:
	def request_activity_summary_leaderboard_data(self, game_id:c_int=0, query_type:c_int=1, results_end:c_int=10, results_start:c_int=0, target:c_int64=None, weekly:bool=None):
		leaderboard = LDF()
		leaderboard.ldf_set("ADO.Result", LDFDataType.BOOLEAN, True)
		leaderboard.ldf_set("Result.Count", LDFDataType.INT32, 0)
		self.send_activity_summary_leaderboard_data(game_id, query_type, leaderboard_data=leaderboard, throttled=False, weekly=False)

	@single
	def send_activity_summary_leaderboard_data(self, game_id:c_int=None, info_type:c_int=None, leaderboard_data:LDF=None, throttled:bool=None, weekly:bool=None):
		pass

	def match_request(self, activator:c_int64=None, player_choices:LDF=None, type:c_int=None, value:c_int=None):
		self.match_response(response=0)
		if type == MatchRequestType.Join:# and value == MatchRequestValue.Join:
			update_data = LDF()
			update_data.ldf_set("time", LDFDataType.FLOAT, 60.0)
			self.match_update(data=update_data, type=MatchUpdateType.Time)

	@single
	def match_response(self, response:c_int=None):
		pass

	@single
	def match_update(self, data:LDF=None, type:c_int=None):
		pass
