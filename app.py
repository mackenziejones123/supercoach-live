from flask import Flask, render_template_string, request, jsonify
import requests
from collections import defaultdict

app = Flask(__name__)

ROUND = 3
API_URL = f"https://www.supercoach.com.au/2026/api/nrl/classic/v1/players-cf?embed=player_stats,positions&round={ROUND}"

TEAM_COLOURS = {
    "Broncos": "#7A003C",
    "Bulldogs": "#0055A4",
    "Storm": "#5E2D79",
    "Panthers": "#000000",
    "Roosters": "#00205B",
    "Sharks": "#00A3E0",
    "Eels": "#003594",
    "Raiders": "#006341",
    "Cowboys": "#002B5C",
    "Titans": "#00205B",
    "Sea Eagles": "#800000",
    "Warriors": "#1D428A",
    "Knights": "#002B5C",
    "Dragons": "#CE1126",
    "Rabbitohs": "#004225",
    "Dolphins": "#D50032",
    "Tigers": "#FF6600"
}

def safe(value):
    return value if value is not None else 0


def get_matches():
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(API_URL, headers=headers, timeout=8)
        data = response.json()
    except Exception as e:
        print("API error:", e)
        return {}, {}

    matches = {}
    team_names = {}

    for player in data:
        stats = player.get("player_stats", [])
        if not stats:
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

        matches[match_key][team_id].append({
            "name": f"{player['first_name']} {player['last_name']}",
            "score": stat.get("livepts") or stat.get("points") or 0,
            "minutes": safe(stat.get("minutes_played")),
            "stats": {
                "Tr": safe(stat.get("tries")),
                "TA": safe(stat.get("try_assists")),
                "TC": safe(stat.get("try_contributions")),
                "LB": safe(stat.get("line_breaks")),
                "LBA": safe(stat.get("line_break_assists")),
                "TB": safe(stat.get("tackle_busts")),
                "FDO": safe(stat.get("forced_drop_outs")),
                "EO": safe(stat.get("effective_offloads")),
                "IO": safe(stat.get("ineffective_offloads")),
                "Tack": safe(stat.get("tackles")),
                "G": safe(stat.get("goals")),
                "FG": safe(stat.get("field_goals")),
                "40/20": safe(stat.get("40_20")),
                "KR": safe(stat.get("kick_regather_break")),
                "HU8": safe(stat.get("hitups_over_8m")),
                "HIG": safe(stat.get("holdups_in_goal")),
                "INT": safe(stat.get("intercepts_taken")),
                "MT": safe(stat.get("missed_tackles")),
                "Err": safe(stat.get("errors")),
                "Pen": safe(stat.get("penalties")),
                "MG": safe(stat.get("missed_goals")),
                "MFG": safe(stat.get("missed_field_goals")),
                "SO": safe(stat.get("sendoffs")),
                "DK": safe(stat.get("dead_kicks"))
            }
        })

    for match in matches.values():
        for team_players in match.values():
            team_players.sort(key=lambda x: x["score"], reverse=True)

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
                "players": {
                    p["name"]: {
                        "score": p["score"],
                        "minutes": p["minutes"]
                    }
                    for p in players
                }
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
<title>SuperCoach Live</title>
<style>

:root {{
    --bg: #0f1115;
    --card: #1b212c;
    --text: #f0f3f8;
    --subtle: #aaa;
    --green: #2ecc71;
    --red: #ff4d4d;
}}

.light-mode {{
    --bg: #f4f6f9;
    --card: #ffffff;
    --text: #111;
    --subtle: #555;
    --green: #1e9e5a;
    --red: #d63031;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    padding:20px;
    background: var(--bg);
    color: var(--text);
    transition: all 0.3s ease;
}}

.container {{
    display:flex;
    gap:40px;
}}

.team {{
    width:50%;
}}

.team-header {{
    margin-bottom:18px;
}}

.team-name {{
    font-size:22px;
    font-weight:700;
}}

.player {{
    margin-top:12px;
    padding:14px;
    border-radius:10px;
    background:var(--card);
    transition: all 0.25s ease;
}}

.player:hover {{
    transform: translateY(-2px);
}}

.player-inner {{
    display:flex;
    justify-content:space-between;
    align-items:center;
}}

.score {{
    font-size:24px;
    font-weight:900;
    transition: all 0.2s ease;
}}

.score.flash {{
    animation: scorePop 0.4s ease;
    text-shadow: 0 0 10px var(--green);
}}

@keyframes scorePop {{
    0% {{ transform: scale(1); }}
    50% {{ transform: scale(1.2); }}
    100% {{ transform: scale(1); }}
}}

.minutes {{
    font-size:12px;
    color:var(--subtle);
    margin-left:8px;
}}

.stats {{
    font-size:12px;
    margin-top:10px;
    line-height:1.8;
}}

.pos {{
    color:var(--green);
    margin-right:12px;
    font-weight:600;
}}

.neg {{
    color:var(--red);
    margin-right:12px;
    font-weight:600;
}}

.hidden {{
    display:none;
}}

button {{
    margin-top:10px;
    padding:8px 14px;
    background:var(--card);
    color:var(--text);
    border:1px solid #333;
    border-radius:6px;
    cursor:pointer;
}}

select {{
    padding:8px;
    background:var(--card);
    color:var(--text);
    border:1px solid #333;
    border-radius:6px;
}}

</style>
</head>
<body>

<h2>Round {ROUND} • Live</h2>

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
<button onclick="toggleTheme()">Toggle Theme</button>
"""

    if selected and selected in matches:
        team1, team2 = selected
        html += '<div class="container">'

        for team_id in [team1, team2]:
            team_name = team_names[team_id]
            colour = TEAM_COLOURS.get(team_name, "#444")
            players = matches[selected].get(team_id, [])

            html += f'''
            <div class="team">
                <div class="team-header" style="border-bottom:2px solid {colour}; padding-bottom:8px;">
                    <div class="team-name" style="color:{colour};">{team_name}</div>
                </div>
            '''

            for p in players:
                positive_keys = ["Tr","TA","TC","LB","LBA","TB","FDO","EO","IO","Tack","G","FG","40/20","KR","HU8","HIG","INT"]
                negative_keys = ["MT","Err","Pen","MG","MFG","SO","DK"]

                positive_stats = " ".join(
                    [f"<span class='pos'>{k}:{p['stats'][k]}</span>" for k in positive_keys]
                )

                negative_stats = " ".join(
                    [f"<span class='neg'>{k}:{p['stats'][k]}</span>" for k in negative_keys]
                )

                html += f'''
                <div class="player" style="border-left:4px solid {colour};">
                    <div class="player-inner">
                        <div>
                            <strong>{p["name"]}</strong>
                        </div>
                        <div>
                            <span class="score" data-player="{p["name"]}">{p["score"]}</span>
                            <span class="minutes">({p["minutes"]}m)</span>
                        </div>
                    </div>

                    <div class="stats">
                        <div>{positive_stats}</div>
                        <div>{negative_stats}</div>
                    </div>
                </div>
                '''

            html += '</div>'

        html += '</div>'

    html += """
<script>
let previousScores = {};

function toggleStats() {
    document.querySelectorAll(".stats").forEach(s => {
        s.classList.toggle("hidden");
    });
}

function toggleTheme() {
    document.body.classList.toggle("light-mode");
    localStorage.setItem("theme",
        document.body.classList.contains("light-mode") ? "light" : "dark"
    );
}

window.onload = function() {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
    }
};

async function pollData() {
    const response = await fetch("/data");
    const data = await response.json();

    for (const matchKey in data) {
        for (const teamId in data[matchKey]) {
            const players = data[matchKey][teamId].players;

            for (const playerName in players) {
                const playerData = players[playerName];
                const scoreElement = document.querySelector(`[data-player="${playerName}"]`);

                if (scoreElement) {
                    const previous = previousScores[playerName];
                    if (previous !== undefined && playerData.score > previous) {
                        scoreElement.classList.add("flash");
                        setTimeout(() => scoreElement.classList.remove("flash"), 400);
                    }
                    scoreElement.innerText = playerData.score;
                    previousScores[playerName] = playerData.score;
                }
            }
        }
    }
}

setInterval(pollData, 10000);
pollData();
</script>

</body></html>
"""

    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)