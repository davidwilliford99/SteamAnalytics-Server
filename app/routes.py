from flask import Blueprint, request, jsonify
from .models import get_db
from .utils import (
    fetch_steam_user_details,
    get_steam_user,
    get_friends_list,
    get_most_played,
    top_categories,
    rare_achievements,
    total_hours,
    average_hours_per_week,
    library_value,
    get_game_details,
    get_featured_games,
    get_apps_in_genre
)

main = Blueprint('main', __name__)

@main.route('/add_user/<steam_id>', methods=['POST'])
def add_user(steam_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT steam_id FROM users WHERE steam_id = ?', (steam_id,))
        if cursor.fetchone():
            return jsonify({'error': 'User already exists'}), 409
        cursor.execute('INSERT INTO users (steam_id) VALUES (?)', (steam_id,))
        conn.commit()
        return jsonify({'message': 'User added'}), 201
    finally:
        conn.close()

@main.route('/users')
def list_users():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT steam_id FROM users')
        users = cursor.fetchall()
        user_details = []
        for user in users:
            steam_id = user[0]
            details = fetch_steam_user_details(steam_id)
            if 'error' not in details:
                user_info = {
                    'steam_id': steam_id,
                    'personaname': details.get('personaname', 'N/A'),
                    'avatarmedium': details.get('avatarmedium', 'N/A')
                }
                user_details.append(user_info)
            else:
                user_details.append({'steam_id': steam_id, 'error': details['error']})
        return jsonify({'users': user_details})
    finally:
        conn.close()

@main.route('/steam/api/user', methods=['GET'])
def get_steam_user_route():
    steam_id = request.args.get('steamid')
    return jsonify(get_steam_user(steam_id))

@main.route('/steam/api/friends', methods=['GET'])
def get_friends_list_route():
    steam_id = request.args.get('steamid')
    amount = request.args.get('amount', 10)
    return jsonify(get_friends_list(steam_id, amount))

@main.route('/steam/api/most-played', methods=['GET'])
def get_most_played_route():
    steam_id = request.args.get('steamid')
    return jsonify(get_most_played(steam_id))

@main.route('/steam/api/top_categories', methods=['GET'])
def top_categories_route():
    steam_id = request.args.get('steamid')
    return jsonify(top_categories(steam_id))

@main.route('/steam/api/rare-achievements', methods=['GET'])
def rare_achievements_route():
    steam_id = request.args.get('steamid')
    return jsonify(rare_achievements(steam_id))

@main.route('/steam/api/total-hours', methods=['GET'])
def total_hours_route():
    steam_id = request.args.get('steamid')
    return jsonify(total_hours(steam_id))

@main.route('/steam/api/average-hours-per-week', methods=['GET'])
def average_hours_per_week_route():
    steam_id = request.args.get('steamid')
    return jsonify(average_hours_per_week(steam_id))

@main.route('/steam/api/library-value', methods=['GET'])
def library_value_route():
    steam_id = request.args.get('steamid')
    return jsonify(library_value(steam_id))

@main.route('/steam/api/game-details', methods=['GET'])
def get_game_details_route():
    appid = request.args.get('appid')
    return jsonify(get_game_details(appid))

@main.route('/steam/api/featured-games/', methods=['GET'])
def get_featured_games_route():
    return jsonify(get_featured_games())

@main.route('/steam/api/apps-in-genre', methods=['GET'])
def get_apps_in_genre_route():
    genre = request.args.get('genre')
    return jsonify(get_apps_in_genre(genre))
