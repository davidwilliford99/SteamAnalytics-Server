from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import requests
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





if __name__ == '__main__':
    app.run(debug=True)
