from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
from flask_cors import CORS
from math import floor
import requests
import time
import os


app = Flask(__name__)
CORS(app) 


# Steam API Key
load_dotenv()
api_key = os.getenv("STEAM_API_KEY")



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
        return jsonify({'error': 'appid parameter is required'}), 400

    steam_url = f'http://store.steampowered.com/api/appdetails?appids={appid}'
    response = requests.get(steam_url)
    data = response.json()

    if not data.get(appid, {}).get('success', False):
        return jsonify({'error': 'Failed to fetch game details or game not found'}), 404

    game_data = data[appid]['data']

    # Parsing the desired fields
    details = {
        'steam_appid': game_data.get('steam_appid'),
        'images': {
            'header_image': game_data.get('header_image'),
            'background': game_data.get('background'),
            'background_raw': game_data.get('background_raw'),
        },
        'pc_requirements': game_data.get('pc_requirements', {}).get('recommended'),
        'developers': game_data.get('developers', []),
        'publishers': game_data.get('publishers', []),
        'categories': [{'id': category['id'], 'description': category['description']} for category in game_data.get('categories', [])],
        'screenshots': [{'id': screenshot['id'], 'path_thumbnail': screenshot['path_thumbnail'], 'path_full': screenshot['path_full']} for screenshot in game_data.get('screenshots', [])],
        'movies': [{'id': movie['id'], 'name': movie['name'], 'thumbnail': movie['thumbnail'], 'webm': movie['webm'], 'mp4': movie['mp4']} for movie in game_data.get('movies', [])],
        'achievements': game_data.get('achievements', {}).get('total'),
        'release_date': game_data.get('release_date', {}).get('date'),
        'ratings': game_data.get('ratings', {}),
        # Assuming 'base price' needs to be fetched or calculated separately as it's not directly available in the provided data snippet
        'base_price': 'Price information not available in this dataset',
    }

    return jsonify(details)


if __name__ == '__main__':
    app.run(debug=True)
