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
            "momentum rating <Name>",
            "rising star <Name>",
            "injury report",
            "back to back",
            "game pace",
            "trend player <Name> <Stat> <PropLine>",
            "risk index <Name>",
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
            yield from self.handle_multi_prop_trend(query)
            return


        if q_lower.startswith("momentum rating"):
            yield from self.momentum_rating(query)
            return

        if q_lower.startswith("risk index"):
            yield from self.handle_risk_index(query)
            return
        
        if q_lower.startswith("rising star"):
            yield from self.rising_star_alert(query)
            return

        if "injury report" in q_lower:
            yield from self.injury_watch()
            return


        if "back to back" in q_lower:
            yield from self.back_to_back()
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

    def handle_multi_prop_trend(self, query):
            try:
                parts = query.split()
                if len(parts) < 5:
                    yield {"text": "⚠️ Usage: `trend player <Name> <Stat> <PropLine>` (e.g., trend player LeBron James AST 5.5)"}
                    return

                # Extract
                name = " ".join(parts[2:-2])
                stat = parts[-2].upper()
                prop_line = float(parts[-1])

                stat_map = {
                    "PTS": "PTS",
                    "AST": "AST",
                    "REB": "REB",
                    "3PM": "FG3M"  # 3-point made
                }
                if stat not in stat_map:
                    yield {"text": "⚠️ Stat must be one of: PTS, AST, REB, 3PM."}
                    return

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

                last5 = df.head(5)
                values = last5[stat_map[stat]]
                hits = sum(values > prop_line)
                pct = (hits / 5) * 100

                text = (
                    f"📈 {name.title()} {stat} vs {prop_line}:\n"
                    f"Hit {hits}/5 games ({pct:.0f}%)\n"
                    f"({', '.join(str(int(x)) for x in values)})"
                )
                yield {"text": text}

            except Exception as e:
                logger.error(f"Error in handle_multi_prop_trend: {e}")
                yield {"text": "❌ Error checking trend. Try again."}


    def rising_star_alert(self, query):
        name = query[len("rising star"):].strip()
        matches = players.find_players_by_full_name(name)
        if not matches:
            yield {"text": f"❌ Couldn't find player '{name}'."}
            return

        player_id = matches[0]["id"]
        season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        ).get_data_frames()[0]

        if df.empty:
            yield {"text": f"❌ No games found for {name.title()} in {season}."}
            return

        season_avg = df["PTS"].mean()
        last5_avg = df["PTS"].head(5).mean()
        diff = last5_avg - season_avg

        if diff >= 5:
            yield {"text": f"🚀 Rising Star Alert: {name.title()} averaging +{diff:.1f} PPG over season average!"}
        else:
            yield {"text": f"ℹ️ {name.title()}'s recent PPG change: {diff:.1f} — not a major surge."}

    def injury_watch(self):
        text = "🩼Coming Soon!\n"
        yield {"text": text}

    def momentum_rating(self, query):
        name = query[len("momentum rating"):].strip()
        matches = players.find_players_by_full_name(name)
        if not matches:
            yield {"text": f"❌ Couldn't find player '{name}'."}
            return

        player_id = matches[0]["id"]
        season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        ).get_data_frames()[0]

        if df.empty:
            yield {"text": f"❌ No game logs for {name.title()}."}
            return

        last5 = df.head(5)
        score_sum = (last5["PTS"] + last5["REB"] + last5["AST"]).sum()
        avg_score = score_sum / len(last5)

        if avg_score >= 90:
            label = "Sizzling 🔥"
        elif avg_score >= 70:
            label = "Strong 🏀"
        elif avg_score >= 50:
            label = "Medium 🚶"
        else:
            label = "Cold 🧊"

        text = (
            f"📈 Momentum Rating for {name.title()}:\n"
            f"- Avg (PTS+REB+AST): {avg_score:.1f}\n"
            f"- Rating: {label}"
        )
        yield {"text": text}

    def back_to_back(self):
        sb = scoreboardv2.ScoreboardV2()
        dfs = sb.get_data_frames()
        header_df = dfs[0]

        if header_df.empty:
            yield {"text": "❌ No games found for today."}
            return

        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        text = "⚠️ Possible Back-to-Back Teams:\n"
        found = False
        for game in header_df.itertuples():
            if yesterday_str in game.GAME_DATE_EST:
                text += (
                    f"- {game.HOME_TEAM_ABBREVIATION} or {game.VISITOR_TEAM_ABBREVIATION} played yesterday!\n"
                )
                found = True

        if not found:
            text = "✅ No back-to-back concerns for today."

        yield {"text": text}


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
