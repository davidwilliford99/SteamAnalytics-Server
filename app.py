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
#
@app.route('/steam/api/user', methods=['GET'])
def get_steam_user(steam_id):

    if not steam_id:
        steam_id = request.args.get('steamid') 
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steam_id}'

    try:
        response = requests.get(url)
        response.raise_for_status() 
        return jsonify(response.json()), response.status_code
    
    except requests.RequestException as e:
        return jsonify(error=str(e)), 500



#
# Endpoint for returning Friends list
# Returns steam ids, then steam ids are fed into get_steam_user
# Takes in url param "steamid"
#
@app.route('/steam/api/friends', methods=['GET'])
def get_friends_list():

    steam_id = request.args.get('steamid')
    url = f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={api_key}&steamid={steam_id}&relationship=friend'
    friendsList={}

    # get steam ids from friends list
    try:
        response = requests.get(url)
        response.raise_for_status()
        friendsList = response.json() 
        # return jsonify(response.json()), response.status_code
    
    except requests.RequestException as e:
        return jsonify(error=str(e)), 500

    print(friendsList)


    # TODO
    # send steam ids to return all user info 
    # merge friends info into one object
    # return this object to client






if __name__ == '__main__':
    app.run(debug=True)
