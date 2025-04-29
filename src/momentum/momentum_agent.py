# src/momentum/momentum_agent.py

import logging
from datetime import datetime, timedelta
import numpy as np
import pandas
from sentient_agent_framework.interface.agent import AbstractAgent
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, scoreboardv2
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.endpoints import leaguedashplayerstats
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashplayerclutch
from nba_api.stats.endpoints import playbyplayv2
from nba_api.stats.endpoints import boxscoreadvancedv2


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def detect_season_type():
    now = datetime.now()
    if now.month >= 4 and now.month <= 7:
        return "Playoffs"
    return "Regular Season"

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
            "simulate game <Team1> vs <Team2>",
            "clutch leaders",
            "team momentum <Team Abbreviation>",
            "best overs",
            "best unders",
            "safe picks",
            "consistency player <Name> <Stat> <PropLine>",
            "auto flex",
            "trend breakers",
            "mismatch ratings",
            "fatigue watch",
            "recent plays <GameID>",
            "advanced stats <GameID>",
            "help"
        ]
        }
    
    DEFAULT_PROPS = [
    ("LeBron James", "PTS", 24.5),
    ("Anthony Davis", "REB", 9.5),
    ("Stephen Curry", "3PM", 4.5),
    ("Domantas Sabonis", "REB", 12.5),
    ("Tyrese Haliburton", "AST", 8.5),

]
    

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

        if q_lower.startswith("recent plays"):
            yield from self.get_recent_plays(query)
            return

        if q_lower.startswith("advanced stats"):
            yield from self.get_advanced_boxscore(query)
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
        
        if q_lower.startswith("simulate game"):
            yield from self.simulate_game(query)
            return
        
        if q_lower.startswith("consistency player"):
            yield from self.handle_consistency_tracker(query)
            return

        if "auto flex" in q_lower:
            yield from self.handle_auto_flex_builder()
            return

        
        if q_lower.startswith("team momentum"):
            yield from self.get_team_momentum(query)
            return
        
        if q_lower.startswith("best overs"):
            yield from self.handle_best_overs()
            return

        if q_lower.startswith("best unders"):
            yield from self.handle_best_unders()
            return
        
        if q_lower.startswith("trend breakers"):
            yield from self.handle_auto_trend_breakers()
            return

        if "mismatch ratings" in q_lower:
            yield from self.get_mismatch_ratings()
            return
        
        if "fatigue watch" in q_lower:
            yield from self.check_fatigue_alert()
            return

        if "safe picks" in q_lower:
            yield from self.handle_safe_picks()
            return


        if "clutch leaders" in q_lower:
            yield from self.get_clutch_leaders()
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

    def get_clutch_leaders(self):
        try:

            clutch = leaguedashplayerclutch.LeagueDashPlayerClutch(
                clutch_time="Last 5 Minutes",
                ahead_behind="Ahead or Behind",
                point_diff=5,
                season=f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}",
                season_type_all_star="Regular Season",
                per_mode_detailed="PerGame"
            )

            df = clutch.get_data_frames()[0]
            df = df.sort_values(by="PTS", ascending=False).head(10)

            text = "🧠 Top Clutch Scorers (Last 5 min, Close Games):\n"
            for i, row in enumerate(df.itertuples(), start=1):
                text += f"{i}. {row.PLAYER_NAME}: {row.PTS:.1f} PPG\n"

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error fetching clutch leaders: {e}")
            yield {"text": "❌ Error fetching clutch leaders."}

    def handle_consistency_tracker(self, query):
        try:
            parts = query.split()
            if len(parts) < 5:
                yield {"text": "⚠️ Usage: `consistency player <Name> <Stat> <PropLine>` (e.g., consistency player Chris Paul AST 7.5)"}
                return

            name = " ".join(parts[2:-2])
            stat = parts[-2].upper()
            prop_line = float(parts[-1])

            stat_map = {
                "PTS": "PTS",
                "AST": "AST",
                "REB": "REB",
                "3PM": "FG3M"
            }
            if stat not in stat_map:
                yield {"text": "⚠️ Stat must be one of: PTS, AST, REB, 3PM."}
                return

            matches = players.find_players_by_full_name(name)
            if not matches:
                yield {"text": f"❌ Couldn't find player '{name}'."}
                return

            player_id = matches[0]["id"]
            df = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}",
                season_type_all_star=detect_season_type()
            ).get_data_frames()[0]

            if df.empty:
                yield {"text": f"❌ No game logs found for {name.title()}."}
                return

            df = df.sort_values(by="GAME_DATE", ascending=False)
            last30 = df.head(10)  # Approx 30 days = ~10 games

            values = last30[stat_map[stat]]
            hits = sum(values > prop_line)
            pct = (hits / len(last30)) * 100

            text = (
                f"📚 Consistency Tracker for {name.title()} ({stat} > {prop_line}):\n"
                f"- Hit {hits}/{len(last30)} games ({pct:.0f}%) over last 30 days."
            )
            yield {"text": text}
        except Exception as e:
            logger.error(f"Error in handle_consistency_tracker: {e}")
            yield {"text": "❌ Error checking consistency."}


    def get_mismatch_ratings(self):
        try:
            from nba_api.stats.endpoints import leaguedashteamstats

            df = leaguedashteamstats.LeagueDashTeamStats(
                season=f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}",
                season_type_all_star=detect_season_type(),
                per_mode_detailed="PerGame",
                measure_type_detailed_defense="Defense"  
            ).get_data_frames()[0]


            df = df.sort_values(by="DEF_RATING", ascending=False) 
            bottom5 = df.head(5)

            text = "🎯 Defensive Mismatches (Bottom 5 Teams):\n"
            for row in bottom5.itertuples():
                text += f"- {row.TEAM_NAME}: {row.DEF_RATING:.1f} Defensive Rating\n"

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error fetching mismatch ratings: {e}")
            yield {"text": "❌ Error fetching mismatch ratings."}

    def get_recent_plays(self, query):
        try:
            game_id = query.strip().split("recent plays")[-1].strip()

            pbp = playbyplayv2.PlayByPlayV2(game_id=game_id)
            df = pbp.get_data_frames()[0]

            if df.empty:
                yield {"text": "❌ No recent plays found for this game ID."}
                return

            last10 = df.tail(10)

            text = "⏱️ Last 10 Plays:\n"
            for row in last10.itertuples():
                text += f"- {row.PCTIMESTRING} {row.HOMEDESCRIPTION or ''} {row.VISITORDESCRIPTION or ''}\n"

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error fetching recent plays: {e}")
            yield {"text": "❌ Error fetching recent plays."}



    def get_advanced_boxscore(self, query):
        try:
            game_id = query.strip().split("advanced stats")[-1].strip()

            box = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id)
            df = box.get_data_frames()[0]

            if df.empty:
                yield {"text": "❌ No advanced stats found for this game ID."}
                return

            text = "📊 Advanced Box Score:\n"
            for row in df.itertuples():
                text += (
                    f"- {row.TEAM_ABBREVIATION}: "
                    f"OffRtg {row.OFF_RATING:.1f}, "
                    f"DefRtg {row.DEF_RATING:.1f}, "
                    f"Pace {row.PACE:.1f}\n"
                )

            yield {"text": text}
        except Exception as e:
            logger.error(f"Error fetching advanced box: {e}")
            yield {"text": "❌ Error fetching advanced stats."}



    def check_fatigue_alert(self):
        try:

            today = datetime.now()
            yesterday = today - timedelta(days=1)
            yesterday_str = yesterday.strftime("%Y-%m-%d")

            sb = scoreboardv2.ScoreboardV2(
                game_date=today.strftime("%m/%d/%Y")
            )
            games_today = sb.get_data_frames()[0]
            games_today.columns = [c.upper() for c in games_today.columns]

            text = "🩼 Fatigue Watch Today:\n"
            found = False

            for game in games_today.itertuples():
                for team_id in [game.HOME_TEAM_ID, game.VISITOR_TEAM_ID]:
                    team_list = teams.get_teams()
                    team_info = next((t for t in team_list if t['id'] == team_id), None)
                    if not team_info:
                        continue

                    team_abbr = team_info['abbreviation']

                    gamelog = teamgamelog.TeamGameLog(
                        team_id=team_id,
                        season=f"{today.year-1}-{str(today.year)[-2:]}",
                        season_type_all_star=detect_season_type()
                    ).get_data_frames()[0]

                    recent = gamelog[gamelog['GAME_DATE'] >= yesterday_str]
                    if not recent.empty:
                        text += f"- {team_abbr}: Played yesterday ⚠️\n"
                        found = True


            if not found:
                text += "✅ No fatigue concerns detected."

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error checking fatigue: {e}")
            yield {"text": "❌ Error checking fatigue."}



    def handle_auto_flex_builder(self):
        try:
            candidates = [
                ("LeBron James", "PTS", 24.5),
                ("Anthony Davis", "REB", 9.5),
                ("Stephen Curry", "3PM", 4.5),
                ("Domantas Sabonis", "REB", 12.5),
                ("Tyrese Haliburton", "AST", 8.5),
                ("Devin Booker", "PTS", 27.5),
                ("Jayson Tatum", "REB", 8.5),
                ("Luka Doncic", "AST", 8.5),
                ("James Harden", "AST", 8.5),
                ("Jimmy Butler", "PTS", 21.5),
            ]

            slip = []
            for name, stat, prop_line in candidates:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue
                player_id = matches[0]["id"]
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}",
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]
                if df.empty:
                    continue
                df = df.sort_values(by="GAME_DATE", ascending=False)
                last5 = df.head(5)

                stat_map = {
                    "PTS": "PTS",
                    "REB": "REB",
                    "AST": "AST",
                    "3PM": "FG3M"
                }
                values = last5[stat_map[stat]]
                hits = sum(values > prop_line)
                pct = (hits/5) * 100

                if pct >= 80:
                    slip.append(f"- {name} Over {prop_line} {stat} ({pct:.0f}%)")

                if len(slip) == 5:
                    break

            if not slip:
                yield {"text": "⚠️ No strong Auto Flex picks today."}
                return

            text = "🤖 Auto Flex Picks (80%+ hit rate):\n" + "\n".join(slip)
            yield {"text": text}
        except Exception as e:
            logger.error(f"Error in handle_auto_flex_builder: {e}")
            yield {"text": "❌ Error generating auto flex picks."}

    def handle_auto_trend_breakers(self):
        """
        Auto-detect top 5 trend breakers (biggest underperformers and overperformers)
        """
        text = "⚡ Trend Breakers & Hot Streaks:\n"
        try:
            player_list = [
                "LeBron James", "Stephen Curry", "Kevin Durant", "Devin Booker", "Jayson Tatum",
                "Giannis Antetokounmpo", "Jimmy Butler", "Anthony Davis", "Damian Lillard", "Tyrese Haliburton"
            ]

            entries = []

            for name in player_list:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue

                player_id = matches[0]["id"]
                season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]

                if df.empty:
                    continue

                df = df.sort_values(by="GAME_DATE", ascending=False)
                season_avg = df["PTS"].mean()
                last_game = df.iloc[0]

                pts = last_game["PTS"]
                diff = pts - season_avg
                pct_change = (diff / season_avg) * 100

                entries.append((name, pts, season_avg, pct_change))

            # Sort by biggest % change
            entries.sort(key=lambda x: abs(x[3]), reverse=True)

            top5 = entries[:5]

            for name, pts, season_avg, pct in top5:
                if pct < -20:
                    text += f"❌ {name}: scored {pts} pts ({pct:.0f}% below avg)\n"
                elif pct > 20:
                    text += f"🔥 {name}: scored {pts} pts ({pct:.0f}% above avg)\n"

            if not top5:
                text = "⚠️ No major trend breakers found today."

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error in handle_auto_trend_breakers: {e}")
            yield {"text": "❌ Error finding trend breakers."}



    def handle_best_overs(self):
        try:
            names = ["LeBron James", "Anthony Davis", "Jayson Tatum", "Stephen Curry", "Devin Booker"]
            text = "🔥 Best OVER Performers (last 5 games):\n"
            found = False  # <-- ADDED
            for name in names:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue
                player_id = matches[0]["id"]
                season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]

                if df.empty:
                    continue

                df = df.sort_values(by="GAME_DATE", ascending=False)
                last5 = df.head(5)["PTS"]
                prop_line = last5.mean() * 0.9
                hits = sum(last5 > prop_line)
                pct = (hits/5) * 100

                if pct >= 60:
                    text += f"- {name}: Over {prop_line:.1f} pts → {hits}/5 ({pct:.0f}%)\n"
                    found = True

            if not found:
                text += "\n⚠️ No strong overs available today."

            yield {"text": text}
        except Exception as e:
            logger.error(f"Error in handle_best_overs: {e}")
            yield {"text": "❌ Error generating best overs."}



    def handle_best_unders(self):
        try:
            names = ["James Harden", "Chris Paul", "DeMar DeRozan", "Jimmy Butler", "Russell Westbrook"]
            text = "❄️ Best UNDER Performers (last 5 games):\n"
            for name in names:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue
                player_id = matches[0]["id"]
                season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]
                if df.empty:
                    continue
                last5 = df.sort_values(by="GAME_DATE", ascending=False).head(5)["PTS"]
                prop_line = last5.mean() * 1.1  # Assume prop ~10% higher than avg points
                misses = sum(last5 < prop_line)
                pct = (misses/5)*100
                if pct >= 60:
                    text += f"- {name}: Under {prop_line:.1f} pts → {misses}/5 ({pct:.0f}%)\n"
            yield {"text": text}
        except Exception as e:
            logger.error(f"Error in handle_best_unders: {e}")
            yield {"text": "❌ Error generating best unders."}


    def handle_safe_picks(self):
        text = "✅ Safe Picks (80%+ hit rate over/under):\n"
        found = False

        for name, stat, prop_line in self.DEFAULT_PROPS:
            try:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue

                player_id = matches[0]["id"]
                season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]

                if df.empty:
                    continue

                last5 = df.sort_values(by="GAME_DATE", ascending=False).head(5)

                stat_map = {
                    "PTS": "PTS",
                    "REB": "REB",
                    "AST": "AST",
                    "3PM": "FG3M"
                }
                if stat not in stat_map:
                    continue

                values = last5[stat_map[stat]]
                hits = sum(values > prop_line)
                pct = (hits / 5) * 100

                if pct >= 80:
                    text += f"- {name} Over {prop_line} {stat}: {hits}/5 ({pct:.0f}%)\n"
                    found = True

            except Exception as e:
                logger.error(f"Error in handle_safe_picks for {name}: {e}")
                continue

        if not found:
            text = "⚠️ No 'safe picks' (80%+ hit) available today."

        yield {"text": text}


    def handle_best_overs(self):
        try:
            text = "🔥 Best OVER Performers (last 5 games):\n"
            found = False

            for name, stat, prop_line in self.DEFAULT_PROPS:
                matches = players.find_players_by_full_name(name)
                if not matches:
                    continue

                player_id = matches[0]["id"]
                season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
                df = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]

                if df.empty:
                    continue

                df = df.sort_values(by="GAME_DATE", ascending=False)
                last5 = df.head(5)

                stat_map = {
                    "PTS": "PTS",
                    "REB": "REB",
                    "AST": "AST",
                    "3PM": "FG3M"
                }

                if stat not in stat_map:
                    continue

                values = last5[stat_map[stat]]
                hits = sum(values > prop_line)
                pct = (hits / 5) * 100

                if pct >= 60:
                    text += f"- {name}: Over {prop_line} {stat} → {hits}/5 ({pct:.0f}%)\n"
                    found = True

            if not found:
                text += "\n⚠️ No strong overs available today."

            yield {"text": text}

        except Exception as e:
            logger.error(f"Error in handle_best_overs: {e}")
            yield {"text": "❌ Error generating best overs."}





    def simulate_game(self, query):
        try:
            parts = query[len("simulate game"):].strip().split(" vs ")
            if len(parts) != 2:
                yield {"text": "⚠️ Usage: `simulate game <Team1> vs <Team2>`"}
                return
            
            team1 = parts[0].strip().title()
            team2 = parts[1].strip().title()

            ratings = self.get_team_offensive_ratings()

            if not ratings:
                yield {"text": "❌ Could not load team ratings."}
                return

            avg_pace = 100  # keep simple for now

            team1_rating = ratings.get(team1, 110)
            team2_rating = ratings.get(team2, 110)

            team1_score = int((avg_pace * team1_rating) / 100)
            team2_score = int((avg_pace * team2_rating) / 100)

            text = f"🎮 Simulated Final Score (real ratings):\n\n{team1} {team1_score} – {team2_score} {team2}"
            yield {"text": text}

        except Exception as e:
            logger.error(f"Error in simulate_game: {e}")
            yield {"text": "❌ Error simulating game. Try again."}



    def get_team_offensive_ratings(self):
        try:
            teams = leaguedashteamstats.LeagueDashTeamStats(season=f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}")
            df = teams.get_data_frames()[0]
            ratings = {}

            for row in df.itertuples():
                ratings[row.TEAM_NAME] = getattr(row, "OFF_RATING", getattr(row, "OFFENSIVE_RATING", None))


            return ratings
        except Exception as e:
            logger.error(f"Error fetching team ratings: {e}")
            return {}


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
                    season_type_all_star=detect_season_type()
                ).get_data_frames()[0]
                df = df.sort_values(by="GAME_DATE", ascending=False)

                if df.empty:
                    yield {"text": f"❌ No game logs for {name.title()} in {season}."}
                    return

                last5 = df.sort_values(by="GAME_DATE", ascending=False).head(5)
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
            season_type_all_star=detect_season_type()
        ).get_data_frames()[0]
        df = df.sort_values(by="GAME_DATE", ascending=False)

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
            season_type_all_star=detect_season_type()
        ).get_data_frames()[0]
        df = df.sort_values(by="GAME_DATE", ascending=False)

        if df.empty:
            yield {"text": f"❌ No game logs for {name.title()}."}
            return

        last5 = df.sort_values(by="GAME_DATE", ascending=False).head(5)
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
            season_type_all_star=detect_season_type()
        ).get_data_frames()[0]
        df = df.sort_values(by="GAME_DATE", ascending=False)

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
            season_type_all_star=detect_season_type()
        ).get_data_frames()[0]
        df = df.sort_values(by="GAME_DATE", ascending=False)

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

        text = "Projected Game Pace:\n"
        for game in header_df.itertuples():
            pace = getattr(game, "POSS", None)
            if pace is None or (isinstance(pace, float) and np.isnan(pace)):
                continue
            text += f"{game.HOME_TEAM_ABBREVIATION} vs {game.VISITOR_TEAM_ABBREVIATION}: {pace:.1f} possessions\n"

        if text == "Projected Game Pace:\n":
            text = "⚠️ No possession data available for today."

        yield {"text": text}
