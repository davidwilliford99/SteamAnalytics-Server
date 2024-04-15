from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from math import floor
import requests
import time
import os


app = Flask(__name__)
CORS(app)

#
# Initial Config
# =================================================================================
#

# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steamdata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initializing DB
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created.")


# User model
class User(db.Model):
    steam_id = db.Column(db.String(80), primary_key=True)
    def __repr__(self):
        return f'<User steam_id={self.steam_id}>'


# =================================================================================





# Steam API Key
load_dotenv()
api_key = os.getenv("STEAM_API_KEY")



#
# Adding Users Endpoint
#
@app.route('/add_user/<steam_id>', methods=['POST'])
def add_user(steam_id):
    if User.query.get(steam_id):
        return 'User already exists'
    new_user = User(steam_id=steam_id)
    db.session.add(new_user)
    db.session.commit()
    return 'User added'


#
# List existing users endpoint
#
@app.route('/users')
def list_users():
    users = User.query.all()
    return '<br>'.join([user.steam_id for user in users])





#
# API route for getting Steam Account Info
# Takes in url param "steamid"
# Optional input parameter 'steamid' if called internally
#
@app.route('/steam/api/user', methods=['GET'])
def get_steam_user(steam_id=None):
    if not steam_id:
        steam_id = request.args.get('steamid')

    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steam_id}'

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()  # Always fetch the data

    except requests.RequestException as e:
        return {"error": str(e)}
    
    # If the function detects it's directly responding to an HTTP request, return a Flask response
    if 'steamid' in request.args and not steam_id:
        return jsonify(data), 200

    # Otherwise, just return the data for internal use
    return data



#
# Endpoint for returning Friends list
# Returns steam ids, then steam ids are fed into get_steam_user
# Takes in url param "steamid"
#
@app.route('/steam/api/friends', methods=['GET'])
def get_friends_list():

    steam_id = request.args.get('steamid')
    amount = int(request.args.get('amount', '10'))
    print(amount)
    friends_list = []

    url = f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={api_key}&steamid={steam_id}&relationship=friend'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        friends_list = response.json()["friendslist"]["friends"]

    except requests.RequestException as e:
        return jsonify(error=str(e)), 500

    friends_info = []

    for friend in friends_list[:amount]:
        friend_id = friend["steamid"]
        friend_data = get_steam_user(friend_id)
        if 'error' not in friend_data:
            # This check is crucial to ensure that you're accessing 'response' on a valid data structure
            if 'response' in friend_data and 'players' in friend_data['response']:
                friends_info.append(friend_data['response']['players'][0])
            else:
                print(f"No player data found for {friend_id}")
        else:
            print(f"Error fetching data for {friend_id}: {friend_data['error']}")

        if len(friends_info) >= amount:
            break

    return jsonify(friends_info)




#
# Getting most played games
# URL params: 'steamid' 
#
@app.route('/steam/api/most-played', methods=['GET'])
def get_most_played():
    steam_id = request.args.get('steamid')

    if not steam_id:
        return jsonify({"error": "Steam ID is required"}), 400

    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&format=json&include_played_free_games=1&include_appinfo=1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        games = data.get("response", {}).get("games", [])

        # Correctly filter out games with 0 playtime and sort by playtime_forever
        filtered_games = [game for game in games if game.get("playtime_forever", 0) > 0]
        filtered_games.sort(key=lambda x: x.get("playtime_forever", 0), reverse=True)
        top_games = filtered_games[:20]

        # Prepare the response with the necessary details
        most_played_games = [
            {
                "appid": game["appid"],
                "title": game["name"], 
                "imageurl": f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/header.jpg",
                "playtime_forever": game["playtime_forever"]
            } for game in top_games
        ]
        
        return jsonify(most_played_games)
    
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500



#
# Endpoint to return top 3 categories
# Takes in url param steamid
#
@app.route('/steam/api/top_categories', methods=['GET'])
def top_categories():

    steam_id = request.args.get('steamid')

    owned_games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&include_appinfo=true&format=json"
    response = requests.get(owned_games_url)
    games_data = response.json().get('response', {}).get('games', [])
    
    # Sort games by playtime and limit to top 10
    top_games = sorted(games_data, key=lambda x: x['playtime_forever'], reverse=True)[:10]

    # Fetch game details and collect genres
    genres_count = {}
    exclude_keywords = ['Steam', 'support', 'controller']

    for game in top_games:
        app_details_url = f"http://store.steampowered.com/api/appdetails?appids={game['appid']}"
        details_response = requests.get(app_details_url)

        details_data = details_response.json().get(str(game['appid']), {}).get('data', {})
        
        for genre in details_data.get('genres', []):
            description = genre.get('description')
            if description and not any(keyword.lower() in description.lower() for keyword in exclude_keywords):
                genres_count[description] = genres_count.get(description, 0) + 1
    
    # Determine top 3 genres
    top_genres = sorted(genres_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return jsonify(top_genres)




#
# Helper methods
#
def get_owned_games(steamid):
    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steamid}&format=json&include_played_free_games=1&include_appinfo=1'
    response = requests.get(url)
    return response.json()

def get_global_achievements(gameid):
    url = f'http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid={gameid}&format=json'
    response = requests.get(url)
    return response.json()

def get_player_achievements(gameid, steamid):
    url = f'http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={gameid}&key={api_key}&steamid={steamid}'
    response = requests.get(url)
    return response.json()

def get_player_summaries(steamid):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steamid}'
    response = requests.get(url)
    return response.json()

def get_game_price(appid):
    url = f'http://store.steampowered.com/api/appdetails?appids={appid}&filters=price_overview,basic'
    response = requests.get(url)
    data = response.json()
    if data[str(appid)]['success']:
        game_data = data[str(appid)]['data']
        # Check if the item is a game
        if 'type' in game_data and game_data['type'] == 'game':
            if 'price_overview' in game_data:
                if not game_data['price_overview'].get('is_free', False):
                    price_in_cents = game_data['price_overview']['final']
                    price_in_dollars = price_in_cents / 100.0  # Correctly converting cents to dollars
                    return price_in_dollars
    return 0.0




#
# Getting Most Rare Acheivements
# Is split into multiple methods for convinience
# Utilizes above helper methods
#
@app.route('/steam/api/rare-achievements', methods=['GET'])
def rare_achievements():
    steamid = request.args.get('steamid')
    owned_games_response = get_owned_games(steamid)
    
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return jsonify({'error': 'Failed to fetch owned games or no games found.'}), 400

    owned_games = owned_games_response['response']['games']
    rare_achievements_list = []
    
    for game in owned_games:
        game_id = game['appid']
        game_name = game['name']
        global_achievements_response = get_global_achievements(game_id)
        
        # Proceed only if the global achievements response has the expected structure
        if global_achievements_response and 'achievementpercentages' in global_achievements_response and 'achievements' in global_achievements_response['achievementpercentages']:
            global_achievements = global_achievements_response['achievementpercentages']['achievements']
            global_ach_dict = {ach['name']: ach['percent'] for ach in global_achievements}
            
            player_achievements_response = get_player_achievements(game_id, steamid)
            # Ensure player achievements were successfully fetched
            if 'playerstats' in player_achievements_response and 'achievements' in player_achievements_response['playerstats']:
                for player_achievement in player_achievements_response['playerstats']['achievements']:
                    if player_achievement.get('achieved') == 1:
                        ach_name = player_achievement['apiname']
                        if ach_name in global_ach_dict:
                            rare_achievements_list.append({
                                'game': game_name,
                                'achievement': ach_name,
                                'rarity': global_ach_dict[ach_name]
                            })

    # Sort achievements by rarity and return the top 10
    rare_achievements_list.sort(key=lambda x: x['rarity'])
    return jsonify(rare_achievements_list[:10])



#
# Getting total hours
# Takes in url param 'steamid'
#
@app.route('/steam/api/total-hours', methods=['GET'])
def total_hours():
    steamid = request.args.get('steamid')
    if not steamid:
        return jsonify({'error': 'steamid parameter is required'}), 400
    
    owned_games_response = get_owned_games(steamid)
    
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return jsonify({'error': 'Failed to fetch owned games or no games found.'}), 400

    total_playtime_minutes = sum(game['playtime_forever'] for game in owned_games_response['response']['games'])
    total_playtime_hours = total_playtime_minutes / 60  # Convert minutes to hours
    total_playtime_hours_rounded = floor(total_playtime_hours)  # Round down to the nearest whole number
    
    return jsonify({'steamid': steamid, 'total_hours_played': total_playtime_hours_rounded})



#
# Average hours per week
# takes in param 'steamid'
#
@app.route('/steam/api/average-hours-per-week', methods=['GET'])
def average_hours_per_week():
    steamid = request.args.get('steamid')
    if not steamid:
        return jsonify({'error': 'steamid parameter is required'}), 400

    player_summary = get_player_summaries(steamid)
    owned_games_response = get_owned_games(steamid)

    if 'response' not in player_summary or 'players' not in player_summary['response'] or len(player_summary['response']['players']) == 0:
        return jsonify({'error': 'Failed to fetch player summary.'}), 400

    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return jsonify({'error': 'Failed to fetch owned games or no games found.'}), 400

    account_creation = player_summary['response']['players'][0].get('timecreated')
    total_playtime_minutes = sum(game['playtime_forever'] for game in owned_games_response['response']['games'])
    total_playtime_hours = total_playtime_minutes / 60

    if account_creation:
        weeks_since_creation = (time.time() - account_creation) / (60 * 60 * 24 * 7)
        average_hours_per_week = total_playtime_hours / weeks_since_creation
        return jsonify({'steamid': steamid, 'average_hours_per_week': average_hours_per_week})
    else:
        return jsonify({'error': 'Account creation date not available.'}), 400





#
# Getting total library value 
# Takes in url param steamid
#
@app.route('/steam/api/library-value', methods=['GET'])
def library_value():
    steamid = request.args.get('steamid')
    if not steamid:
        return jsonify({'error': 'steamid parameter is required'}), 400
    
    owned_games_response = get_owned_games(steamid)
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return jsonify({'error': 'Failed to fetch owned games or no games found.'}), 400

    total_value = sum(get_game_price(game['appid']) for game in owned_games_response['response']['games'])
    total_value_usd = "{:.2f}".format(total_value)
    return jsonify({'steamid': steamid, 'total_library_value_usd': total_value_usd})



#
# Endpoint for individual game info
# Takes url param 'appid'
#
@app.route('/steam/api/game-details', methods=['GET'])
def get_game_details():
    appid = request.args.get('appid')
    if not appid:
        return jsonify({'error': 'AppID parameter is required'}), 400

    steam_url = f'http://store.steampowered.com/api/appdetails?appids={appid}'
    response = requests.get(steam_url)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to connect to the Steam API'}), response.status_code

    data = response.json()
    if not data.get(appid, {}).get('success', False):
        return jsonify({'error': 'Game details not found'}), 404

    game_data = data[appid]['data']

    # Find the cheapest sub from 'default' package group
    default_package_group = next((group for group in game_data.get('package_groups', []) if group['name'] == 'default'), None)
    cheapest_sub = None
    if default_package_group:
        subs = default_package_group.get('subs', [])
        if subs:
            # Find the sub with the lowest price
            cheapest_sub = min(subs, key=lambda x: x['price_in_cents_with_discount'])
            # Convert price from cents to dollars
            cheapest_sub['price_in_dollars'] = cheapest_sub['price_in_cents_with_discount'] / 100.0

    # Use your original base price logic
    base_price = cheapest_sub['price_in_dollars'] if cheapest_sub else 'Free' if game_data.get('is_free', False) else 'Price information not available'

     # Check if 'pc_requirements' exists and is not empty, otherwise return None
    pc_requirements = game_data.get('pc_requirements', {}).get('recommended') if 'pc_requirements' in game_data and game_data['pc_requirements'] else None


    # Constructing the response
    details = {
        'steam_appid': game_data.get('steam_appid', 'No AppID'),
        'title': game_data.get('name', 'No title available'),
        'genre': [genre['description'] for genre in game_data.get('genres', []) if 'description' in genre],
        'images': {
            'header_image': game_data.get('header_image'),
            'background': game_data.get('background'),
            'background_raw': game_data.get('background_raw')
        },
        'developers': game_data.get('developers', []),
        'publishers': game_data.get('publishers', []),
        'categories': [{'id': cat['id'], 'description': cat['description']} for cat in game_data.get('categories', [])],
        'screenshots': [{'id': sc['id'], 'path_thumbnail': sc['path_thumbnail'], 'path_full': sc['path_full']} for sc in game_data.get('screenshots', [])],
        'movies': [
            {
                'id': movie['id'],
                'name': movie['name'],
                'thumbnail': movie['thumbnail'],
                'webm': movie.get('webm', {}),
                'mp4': movie.get('mp4', {})
            } for movie in game_data.get('movies', [])
        ],
        'achievements': game_data.get('achievements', {}).get('total', 0),
        'release_date': game_data.get('release_date', {}).get('date', 'No release date'),
        'ratings': game_data.get('ratings', {}),
        'pc_requirements': pc_requirements,
        'base_price': base_price
    }

    return jsonify(details), 200  # Successful response with game details







#
# Featured Games (Windows only)
#
@app.route('/steam/api/featured-games/', methods=['GET'])
def get_featured_games():
    url = 'http://store.steampowered.com/api/featured'
    response = requests.get(url)
    data = response.json()
    
    featured_win = data.get('featured_win', [])
    return jsonify(featured_win)



#
# Getting apps for genre 
# takes in url param 'genre'
#
@app.route('/steam/api/apps-in-genre', methods=['GET'])
def get_apps_in_genre():
    genre = request.args.get('genre')
    if not genre:
        return jsonify({'error': 'Genre parameter is required'}), 400

    # Fetching genre-specific game IDs
    url = f'http://store.steampowered.com/api/getappsingenre?genre={genre}'
    response = requests.get(url)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch data'}), response.status_code

    data = response.json()
    full_game_details = []

    # Iterate through tabs like 'featured', 'newreleases', etc.
    for tab_name, tab_content in data.get('tabs', {}).items():
        # Process each game in the tab
        for item in tab_content.get('items', []):
            app_id = item.get('id')
            if app_id:
                # Call local function to fetch details from '/steam/api/game-details'
                game_details = get_game_details_locally(app_id)
                if game_details:
                    full_game_details.append(game_details)

    return jsonify(full_game_details)


#
# Get game details locally
#
def get_game_details_locally(app_id):
    with app.test_request_context(f'?appid={app_id}'):
        response, status_code = get_game_details()
        if status_code == 200:
            return response.get_json()  # Extract the JSON data from the response object
        else:
            return None
        



if __name__ == '__main__':
    app.run(debug=True)

