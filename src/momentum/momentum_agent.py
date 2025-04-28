# src/momentum/momentum_agent.py

import logging
from datetime import datetime
import numpy as np
from sentient_agent_framework.interface.agent import AbstractAgent
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, scoreboardv2
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MomentumAgent(AbstractAgent):
    def __init__(self):
        super().__init__(name="MomentumAgent")

    def list_available_commands(self):
        return {
            "commands": [
                "search player <Name>",
                "hot streaks",
                "risk index <Name>",
                "game pace",
                "help"
            ]
        }

    def assist(self, input_text: str, context: dict):
        query = input_text.strip()
        q_lower = query.lower()

        if not q_lower:
            yield {"text": "👋 Welcome to Momentum! Ask `search player <Name>`, `hot streaks`, `risk index <Name>`, `game pace`, or `help`."}
            return

        if q_lower.startswith("search player"):
            yield from self.handle_search_player(query)
            return
        
        if q_lower.startswith("trend player"):
            yield from self.get_player_trend(query)
            return

        if q_lower.startswith("risk index"):
            yield from self.handle_risk_index(query)
            return

        if "hot streak" in q_lower:
            yield from self.get_hot_streaks()
            return

        if "game pace" in q_lower:
            yield from self.get_game_pace()
            return

        if "help" in q_lower:
            cmds = self.list_available_commands()["commands"]
            yield {"text": "📚 Available Commands:\n" + "\n".join(cmds)}
            return

        yield {"text": "🤔 Try `search player <Name>`, `hot streaks`, `risk index <Name>`, or `game pace`."}

    def get_player_trend(self, query):
        try:
            parts = query.split()
            if len(parts) < 4:
                yield {"text": "⚠️ Usage: `trend player <Name> <prop_line>` (e.g., trend player LeBron James 20.5)"}
                return

            name = " ".join(parts[2:-1])
            prop_line = float(parts[-1])

            matches = players.find_players_by_full_name(name)
            if not matches:
                yield {"text": f"❌ Couldn't find a player named '{name}'."}
                return

            player_id = matches[0]["id"]
            season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
            df = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star="Regular Season"
            ).get_data_frames()[0]

            if df.empty:
                yield {"text": f"❌ No game logs for {name.title()} in {season}."}
                return

            last5_pts = df["PTS"].head(5)
            hits = sum(last5_pts > prop_line)
            pct = (hits / 5) * 100

            text = (
                f"📈 {name.title()} vs {prop_line} pts:\n"
                f"Hit {hits}/5 games ({pct:.0f}%)\n"
                f"({', '.join(str(int(x)) for x in last5_pts)})"

            )
            yield {"text": text}
        except Exception as e:
            logger.error(f"Error in get_player_trend: {e}")
            yield {"text": "❌ Error checking trend. Try again."}


    def handle_search_player(self, query):
        name = query[len("search player"):].strip()
        matches = players.find_players_by_full_name(name)
        if not matches:
            yield {"text": f"❌ Couldn't find a player named '{name}'."}
            return

        player_id = matches[0]["id"]
        season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        ).get_data_frames()[0]

        if df.empty:
            yield {"text": f"❌ No game logs for {name.title()} in {season}."}
            return

        text = f"📊 Last 5 Games for {name.title()} ({season}):\n"
        total_ast = 0
        for _, row in df.head(5).iterrows():
            text += (
                f"{row['GAME_DATE']}: "
                f"{int(row['PTS'])} pts, "
                f"{int(row['AST'])} ast, "
                f"{int(row['REB'])} reb\n"
            )
            total_ast += int(row['AST'])

        avg_ast = total_ast / 5
        text += f"\n➕ Avg Assists (last 5): {avg_ast:.1f}\n"
        yield {"text": text}

    def handle_risk_index(self, query):
        name = query[len("risk index"):].strip()
        matches = players.find_players_by_full_name(name)
        if not matches:
            yield {"text": f"❌ Couldn't find a player named '{name}'."}
            return

        player_id = matches[0]["id"]
        season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        ).get_data_frames()[0]

        if df.empty:
            yield {"text": f"❌ No game logs for {name.title()} in {season}."}
            return

        pts_last10 = df["PTS"].head(10)
        std_dev = np.std(pts_last10)

        if std_dev < 5:
            risk = "🟢 Low Risk (very consistent)"
        elif std_dev < 10:
            risk = "🟡 Medium Risk (some variance)"
        else:
            risk = "🔴 High Risk (volatile)"

        text = (
            f"🎯 Risk Index for {name.title()} ({season}):\n"
            f"STD DEV (last 10 games): {std_dev:.1f}\n"
            f"Rating: {risk}"
        )
        yield {"text": text}

    def get_hot_streaks(self):
        sb = scoreboardv2.ScoreboardV2()
        dfs = sb.get_data_frames()
        header_df = dfs[0]
        line_df = dfs[1]

        if header_df.empty:
            yield {"text": "❌ No games found for today."}
            return

        finals = header_df[header_df["GAME_STATUS_TEXT"] == "Final"]
        if finals.empty:
            yield {"text": "⚠️ No games have finished yet today."}
            return

        text = "🔥 Today's Final Scores:\n"
        for game in finals.itertuples():
            gid = game.GAME_ID
            home_id = game.HOME_TEAM_ID
            visitor_id = game.VISITOR_TEAM_ID

            rows = line_df[line_df["GAME_ID"] == gid]
            home_row = rows[rows["TEAM_ID"] == home_id].iloc[0]
            visitor_row = rows[rows["TEAM_ID"] == visitor_id].iloc[0]

            text += (
                f"{home_row['TEAM_ABBREVIATION']} {int(home_row['PTS'])} – "
                f"{visitor_row['TEAM_ABBREVIATION']} {int(visitor_row['PTS'])}\n"
            )

        yield {"text": text}

    def get_game_pace(self):
        sb = scoreboardv2.ScoreboardV2()
        dfs = sb.get_data_frames()
        header_df = dfs[0]

        if header_df.empty:
            yield {"text": "❌ No games found for today."}
            return

        text = "🏎️ Projected Game Pace:\n"
        for game in header_df.itertuples():
            pace = getattr(game, "POSS", None)
            if pace is None or (isinstance(pace, float) and np.isnan(pace)):
                continue
            text += f"{game.HOME_TEAM_ABBREVIATION} vs {game.VISITOR_TEAM_ABBREVIATION}: {pace:.1f} possessions\n"

        if text == "🏎️ Projected Game Pace:\n":
            text = "⚠️ No possession data available for today."

        yield {"text": text}
