import requests
import os
from math import floor
import time

api_key = os.getenv("STEAM_API_KEY")

def fetch_steam_user_details(steam_id):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steam_id}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        data = response.json()
        return data['response']['players'][0] if data['response']['players'] else {}
    except requests.RequestException as e:
        return {"error": str(e)}

def get_steam_user(steam_id):
    return fetch_steam_user_details(steam_id)

def get_friends_list(steam_id, amount=10):
    url = f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={api_key}&steamid={steam_id}&relationship=friend'
    try:
        response = requests.get(url)
        response.raise_for_status()
        friends_list = response.json()["friendslist"]["friends"]
    except requests.RequestException as e:
        return {"error": str(e)}

    friends_info = []
    for friend in friends_list[:int(amount)]:
        friend_id = friend["steamid"]
        friend_data = get_steam_user(friend_id)
        if 'error' not in friend_data:
            friends_info.append(friend_data)
        if len(friends_info) >= int(amount):
            break
    return friends_info

def get_most_played(steam_id):
    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&format=json&include_played_free_games=1&include_appinfo=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        games = data.get("response", {}).get("games", [])
        filtered_games = [game for game in games if game.get("playtime_forever", 0) > 0]
        filtered_games.sort(key=lambda x: x.get("playtime_forever", 0), reverse=True)
        top_games = filtered_games[:20]

        most_played_games = [
            {
                "appid": game["appid"],
                "title": game["name"],
                "imageurl": f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/header.jpg",
                "playtime_forever": game["playtime_forever"]
            } for game in top_games
        ]
        
        return most_played_games
    
    except requests.RequestException as e:
        return {"error": str(e)}

def top_categories(steam_id):
    owned_games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&include_appinfo=true&format=json"
    try:
        response = requests.get(owned_games_url)
        games_data = response.json().get('response', {}).get('games', [])
        
        top_games = sorted(games_data, key=lambda x: x['playtime_forever'], reverse=True)[:10]

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
        
        top_genres = sorted(genres_count.items(), key=lambda x: x[1], reverse=True)[:5]
        return top_genres
    except requests.RequestException as e:
        return {"error": str(e)}

def rare_achievements(steam_id):
    owned_games_response = get_owned_games(steam_id)
    
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return {'error': 'Failed to fetch owned games or no games found.'}

    owned_games = owned_games_response['response']['games']
    rare_achievements_list = []
    
    for game in owned_games:
        game_id = game['appid']
        game_name = game['name']
        global_achievements_response = get_global_achievements(game_id)
        
        if global_achievements_response and 'achievementpercentages' in global_achievements_response and 'achievements' in global_achievements_response['achievementpercentages']:
            global_achievements = global_achievements_response['achievementpercentages']['achievements']
            global_ach_dict = {ach['name']: ach['percent'] for ach in global_achievements}
            
            player_achievements_response = get_player_achievements(game_id, steam_id)
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

    rare_achievements_list.sort(key=lambda x: x['rarity'])
    return rare_achievements_list[:10]

def total_hours(steam_id):
    owned_games_response = get_owned_games(steam_id)
    
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return {'error': 'Failed to fetch owned games or no games found.'}

    total_playtime_minutes = sum(game['playtime_forever'] for game in owned_games_response['response']['games'])
    total_playtime_hours = total_playtime_minutes / 60
    total_playtime_hours_rounded = floor(total_playtime_hours)
    
    return {'steamid': steam_id, 'total_hours_played': total_playtime_hours_rounded}

def average_hours_per_week(steam_id):
    player_summary = get_player_summaries(steam_id)
    owned_games_response = get_owned_games(steam_id)

    if 'response' not in player_summary or 'players' not in player_summary['response'] or len(player_summary['response']['players']) == 0:
        return {'error': 'Failed to fetch player summary.'}

    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return {'error': 'Failed to fetch owned games or no games found.'}

    account_creation = player_summary['response']['players'][0].get('timecreated')
    total_playtime_minutes = sum(game['playtime_forever'] for game in owned_games_response['response']['games'])
    total_playtime_hours = total_playtime_minutes / 60

    if account_creation:
        weeks_since_creation = (time.time() - account_creation) / (60 * 60 * 24 * 7)
        average_hours_per_week = total_playtime_hours / weeks_since_creation
        return {'steamid': steam_id, 'average_hours_per_week': average_hours_per_week}
    else:
        return {'error': 'Account creation date not available.'}

def library_value(steam_id):
    owned_games_response = get_owned_games(steam_id)
    if not owned_games_response or 'response' not in owned_games_response or 'games' not in owned_games_response['response']:
        return {'error': 'Failed to fetch owned games or no games found.'}

    total_value = sum(get_game_price(game['appid']) for game in owned_games_response['response']['games'])
    total_value_usd = "{:.2f}".format(total_value)
    return {'steamid': steam_id, 'total_library_value_usd': total_value_usd}

def get_game_details(appid):
    if not appid:
        return {'error': 'AppID parameter is required'}

    steam_url = f'http://store.steampowered.com/api/appdetails?appids={appid}'
    try:
        response = requests.get(steam_url)
        response.raise_for_status()

        data = response.json()
        if not data.get(str(appid), {}).get('success', False):
            return {'error': 'Game details not found'}

        game_data = data[str(appid)]['data']

        default_package_group = next((group for group in game_data.get('package_groups', []) if group['name'] == 'default'), None)
        cheapest_sub = None
        if default_package_group:
            subs = default_package_group.get('subs', [])
            if subs:
                cheapest_sub = min(subs, key=lambda x: x['price_in_cents_with_discount'])
                cheapest_sub['price_in_dollars'] = cheapest_sub['price_in_cents_with_discount'] / 100.0

        base_price = cheapest_sub['price_in_dollars'] if cheapest_sub else 'Free' if game_data.get('is_free', False) else 'Price information not available'
        pc_requirements = game_data.get('pc_requirements', {}).get('recommended') if 'pc_requirements' in game_data and game_data['pc_requirements'] else None

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

        return details, 200  # Successful response with game details
    
    except requests.RequestException as e:
        return {'error': str(e)}

def get_featured_games():
    url = 'http://store.steampowered.com/api/featured'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('featured_win', [])
    except requests.RequestException as e:
        return {"error": str(e)}

def get_apps_in_genre(genre):
    if not genre:
        return {'error': 'Genre parameter is required'}

    url = f'http://store.steampowered.com/api/getappsingenre?genre={genre}'
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        full_game_details = []

        for tab_name, tab_content in data.get('tabs', {}).items():
            for item in tab_content.get('items', []):
                app_id = item.get('id')
                if app_id:
                    game_details = get_game_details_locally(app_id)
                    if game_details:
                        full_game_details.append(game_details)

        return full_game_details

    except requests.RequestException as e:
        return {'error': str(e)}

def get_game_details_locally(app_id):
    with app.test_request_context(f'?appid={app_id}'):
        response, status_code = get_game_details(app_id)
        if status_code == 200:
            return response
        else:
            return None

def get_owned_games(steam_id):
    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&format=json&include_played_free_games=1&include_appinfo=1'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def get_global_achievements(game_id):
    url = f'http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid={game_id}&format=json'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def get_player_achievements(game_id, steam_id):
    url = f'http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={game_id}&key={api_key}&steamid={steam_id}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def get_player_summaries(steam_id):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steam_id}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def get_game_price(app_id):
    url = f'http://store.steampowered.com/api/appdetails?appids={app_id}&filters=price_overview,basic'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data[str(app_id)]['success']:
            game_data = data[str(app_id)]['data']
            if 'type' in game_data and game_data['type'] == 'game':
                if 'price_overview' in game_data:
                    if not game_data['price_overview'].get('is_free', False):
                        price_in_cents = game_data['price_overview']['final']
                        price_in_dollars = price_in_cents / 100.0
                        return price_in_dollars
        return 0.0
    
    except requests.RequestException as e:
        return {"error": str(e)}
