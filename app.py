from flask import Flask, render_template_string, request, jsonify
import requests
from collections import defaultdict

app = Flask(__name__)

ROUND = 1
API_URL = f"https://www.supercoach.com.au/2026/api/nrl/classic/v1/players-cf?embed=player_stats,positions&round={ROUND}"

def safe(value):
    return value if value is not None else 0

def get_matches():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(API_URL, headers=headers)
    data = response.json()

    matches = {}
    team_names = {}

    for player in data:
        stats = player.get("player_stats", [])
        positions = player.get("positions", [])
        if not stats or not positions:
            continue

        stat = stats[0]

        if safe(stat.get("games")) == 0 and safe(stat.get("livegames")) == 0:
            continue

        team_id = player["team"]["id"]
        team_name = player["team"]["name"]
        opp = stat.get("opp")
        if not opp:
            continue

        opp_id = opp["id"]
        match_key = tuple(sorted([team_id, opp_id]))

        if match_key not in matches:
            matches[match_key] = defaultdict(list)

        team_names[team_id] = team_name
        team_names[opp_id] = opp["name"]

        position_info = positions[0]

        matches[match_key][team_id].append({
            "name": f"{player['first_name']} {player['last_name']}",
            "score": stat.get("livepts") or stat.get("points") or 0,
            "minutes": safe(stat.get("minutes_played")),
            "position": position_info["position_long"],
            "position_sort": position_info["sort"],

            "tries": safe(stat.get("tries")),
            "try_assists": safe(stat.get("try_assists")),
            "try_contributions": safe(stat.get("try_contributions")),
            "line_breaks": safe(stat.get("line_breaks")),
            "line_break_assists": safe(stat.get("line_break_assists")),
            "tackle_busts": safe(stat.get("tackle_busts")),
            "forced_drop_outs": safe(stat.get("forced_drop_outs")),
            "effective_offloads": safe(stat.get("effective_offloads")),
            "ineffective_offloads": safe(stat.get("ineffective_offloads")),
            "tackles": safe(stat.get("tackles")),
            "goals": safe(stat.get("goals")),
            "field_goals": safe(stat.get("field_goals")),
            "40_20": safe(stat.get("40_20")),
            "kick_regather_break": safe(stat.get("kick_regather_break")),
            "hitups_over_8m": safe(stat.get("hitups_over_8m")),
            "holdups_in_goal": safe(stat.get("holdups_in_goal")),
            "intercepts_taken": safe(stat.get("intercepts_taken")),

            "missed_tackles": safe(stat.get("missed_tackles")),
            "errors": safe(stat.get("errors")),
            "penalties": safe(stat.get("penalties")),
            "missed_goals": safe(stat.get("missed_goals")),
            "missed_field_goals": safe(stat.get("missed_field_goals")),
            "sendoffs": safe(stat.get("sendoffs")),
            "dead_kicks": safe(stat.get("dead_kicks"))
        })

    for match in matches.values():
        for team_players in match.values():
            team_players.sort(key=lambda x: (x["position_sort"], -x["score"]))

    return matches, team_names


@app.route("/data")
def data():
    matches, _ = get_matches()
    output = {}

    for match_key, teams in matches.items():
        key_str = f"{match_key[0]}-{match_key[1]}"
        output[key_str] = {}

        for team_id, players in teams.items():
            output[key_str][str(team_id)] = {
                "total": sum(p["score"] for p in players),
                "players": {p["name"]: p["score"] for p in players}
            }

    return jsonify(output)


@app.route("/")
def home():
    matches, team_names = get_matches()
    match_keys = list(matches.keys())

    selected = request.args.get("match")
    if selected:
        selected = tuple(map(int, selected.split("-")))
    else:
        selected = match_keys[0] if match_keys else None

    html = f"""
<html>
<head>
<title>SuperCoach Live Tracker</title>
<style>
body {{ font-family: Arial; padding:20px; background:#111; color:#eee; }}
.container {{ display:flex; gap:40px; }}
@media(max-width:900px){{ .container{{flex-direction:column;}} .team{{width:100%!important;}} }}

.team {{ width:50%; }}
.team-total {{ font-size:20px; font-weight:bold; color:#00ffcc; margin-bottom:10px; }}
.position {{ margin-top:15px; background:#222; padding:5px; font-weight:bold; }}
.player {{ margin-top:8px; padding:6px; border-radius:6px; background:#1a1a1a; }}
.top-scorer {{ border:1px solid #00ff88; }}

.score {{ float:right; font-weight:bold; }}
.stats {{ font-size:11px; margin-top:4px; }}

.positive {{ color:#00ff88; }}
.negative {{ color:#ff5555; }}

button {{ margin:5px 0; padding:5px 10px; background:#222; color:#fff; border:1px solid #444; cursor:pointer; }}
button:hover {{ background:#333; }}

select {{ padding:5px; margin-bottom:15px; background:#222; color:#fff; border:1px solid #444; }}
.hidden {{ display:none; }}
</style>
</head>
<body>

<h1>Round {ROUND} - SuperCoach Live</h1>

<form method="get">
<select name="match" onchange="this.form.submit()">
"""

    for key in match_keys:
        label = f"{team_names[key[0]]} vs {team_names[key[1]]}"
        value = f"{key[0]}-{key[1]}"
        selected_attr = "selected" if selected == key else ""
        html += f'<option value="{value}" {selected_attr}>{label}</option>'

    html += """
</select>
</form>

<button onclick="toggleStats()">Toggle Stats</button>

<script>
let previousScores = {};

async function pollData() {
    const response = await fetch("/data");
    const data = await response.json();

    for (const matchKey in data) {
        for (const teamId in data[matchKey]) {

            const totalElement = document.querySelector(
                `[data-team-total="${matchKey}_${teamId}"]`
            );

            if (totalElement) {
                totalElement.innerText = "Total: " + data[matchKey][teamId].total;
            }

            const players = data[matchKey][teamId].players;

            for (const playerName in players) {
                const score = players[playerName];

                const scoreElement = document.querySelector(
                    `[data-player="${playerName}"]`
                );

                if (scoreElement) {
                    const previous = previousScores[playerName];

                    if (previous !== undefined && score > previous) {
                        const diff = score - previous;
                        scoreElement.innerHTML = score +
                            `<span style="color:#00ff88; font-size:12px;"> +${diff}</span>`;
                    } else {
                        scoreElement.innerText = score;
                    }

                    previousScores[playerName] = score;
                }
            }
        }
    }
}

function toggleStats(){
    document.querySelectorAll(".stats").forEach(s=>{
        s.classList.toggle("hidden");
    });
}

setInterval(pollData, 10000);
pollData();
</script>
"""

    if selected and selected in matches:
        team1, team2 = selected
        html += '<div class="container">'

        for team_id in [team1, team2]:
            players = matches[selected].get(team_id, [])
            team_total = sum(p["score"] for p in players)
            top_score = max((p["score"] for p in players), default=0)
            match_minutes = max((p["minutes"] for p in players), default=0)

            match_key_str = f"{selected[0]}-{selected[1]}"

            html += f'<div class="team">'
            html += f'<h2>{team_names[team_id]}</h2>'
            html += f'<div class="team-total" data-team-total="{match_key_str}_{team_id}">Total: {team_total}</div>'
            html += f'<div>Match Clock: ~{match_minutes} min</div>'

            current_position = None
            for p in players:
                top_class = "top-scorer" if p["score"] == top_score else ""
                if p["position"] != current_position:
                    current_position = p["position"]
                    html += f'<div class="position">{current_position}</div>'

                html += f'''
                <div class="player {top_class}">
                    <strong>{p["name"]}</strong>
                    <span class="score" data-player="{p["name"]}">{p["score"]}</span>
                    <div class="stats">
                        <span class="positive">Tr:{p["tries"]}</span> |
                        <span class="positive">TA:{p["try_assists"]}</span> |
                        <span class="positive">TC:{p["try_contributions"]}</span> |
                        <span class="positive">LB:{p["line_breaks"]}</span> |
                        <span class="positive">LBA:{p["line_break_assists"]}</span> |
                        <span class="positive">TB:{p["tackle_busts"]}</span> |
                        <span class="positive">FDO:{p["forced_drop_outs"]}</span> |
                        <span class="positive">EO:{p["effective_offloads"]}</span> |
                        <span class="positive">IO:{p["ineffective_offloads"]}</span> |
                        <span class="positive">Tack:{p["tackles"]}</span> |
                        <span class="positive">G:{p["goals"]}</span> |
                        <span class="positive">FG:{p["field_goals"]}</span> |
                        <span class="positive">40/20:{p["40_20"]}</span> |
                        <span class="positive">KR:{p["kick_regather_break"]}</span> |
                        <span class="positive">HU8:{p["hitups_over_8m"]}</span> |
                        <span class="positive">HIG:{p["holdups_in_goal"]}</span> |
                        <span class="positive">INT:{p["intercepts_taken"]}</span> |
                        <span class="negative">MT:{p["missed_tackles"]}</span> |
                        <span class="negative">Err:{p["errors"]}</span> |
                        <span class="negative">Pen:{p["penalties"]}</span> |
                        <span class="negative">MG:{p["missed_goals"]}</span> |
                        <span class="negative">MFG:{p["missed_field_goals"]}</span> |
                        <span class="negative">SO:{p["sendoffs"]}</span> |
                        <span class="negative">DK:{p["dead_kicks"]}</span>
                    </div>
                </div>
                '''

            html += '</div>'

        html += '</div>'

    html += "</body></html>"
    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)