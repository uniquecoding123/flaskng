from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import requests
import datetime

app = Flask(__name__)
CORS(app)

# Secret key for encoding JWT
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
jwt = JWTManager(app)

# ServiceNow credentials and endpoint
servicenow_url = 'https://dev254636.service-now.com/api/now/table/u_demo_user'
servicenow_player_url = 'https://dev254636.service-now.com/api/now/table/u_player'
servicenow_wkt_url = 'https://dev254636.service-now.com/api/now/table/u_wickets'
url = 'https://dev254636.service-now.com/api/now/table/u_highestindivudual'
team_url = 'https://dev254636.service-now.com/api/now/table/u_highestteamscore'
servicenow_user = 'REST'
servicenow_pwd = 'Hardik3393@'

# Headers for ServiceNow API
headers = {"Content-Type": "application/json", "Accept": "application/json"}


@app.route('/register', methods=['POST'])
def register_user():
    user_data = request.get_json()
    u_name = user_data.get('u_name')
    u_password = user_data.get('u_password')
    check_url = f"{servicenow_url}?sysparm_query=u_name={u_name}^u_password={u_password}"
    response = requests.get(check_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

    if response.status_code == 200 and response.json().get('result'):
        # Username and password combination already exists, return an error message
        return jsonify({
            'status': 400,
            'error': 'Username and password combination already exists'
        }), 400

    payload = {"u_name": u_name, "u_password": u_password}

    response = requests.post(servicenow_url, auth=(servicenow_user, servicenow_pwd), headers=headers, json=payload)

    if response.status_code != 201:
        return jsonify({
            'status': response.status_code,
            'error': response.json()
        }), response.status_code

    data = response.json()
    return jsonify(data), 201


@app.route('/login', methods=['POST'])
def login_user():
    login_data = request.get_json()
    u_name = login_data.get('u_name')
    u_password = login_data.get('u_password')

    query_url = f"{servicenow_url}?sysparm_query=u_name={u_name}^u_password={u_password}"
    response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

    if response.status_code != 200:
        return jsonify({
            'status': response.status_code,
            'error': response.json()
        }), response.status_code

    users = response.json().get('result')

    if not users or len(users) == 0:
        return jsonify({"msg": "User not found"}), 404

    user = users[0]

    if user['u_password'] != u_password:
        return jsonify({"msg": "Invalid password"}), 401

    token = create_access_token(identity=user['sys_id'])
    return jsonify(access_token=token)


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    user_sys_id = get_jwt_identity()
    return jsonify(logged_in_as=user_sys_id), 200

#ADD and GET PLAYERS

@app.route('/add_player', methods=['POST'])
@jwt_required()
def add_player():
    try:
        # Get the JSON data from the request
        player_data = request.json

        if not player_data:
            return jsonify({"error": "No data provided"}), 400

        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()

        # Ensure the player data has the required fields
        u_name = player_data.get('u_name')
        u_goals = player_data.get('u_goals')

        if not u_name or not u_goals:
            return jsonify({"error": "Missing required fields"}), 400

        # Query ServiceNow to check if the player already exists
        query_url = f"{servicenow_player_url}?sysparm_query=u_user={user_sys_id}^u_name={u_name}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if players:  # If player exists, add goals to the current goals
            player = players[0]
            player_sys_id = player['sys_id']
            current_goals = player['u_goals'] or 0  # Get the current goals, default to 0 if not available

            # Add the new goals to the current goals
            new_goals = int(current_goals) + int(u_goals)

            # Update player goals with the new total
            update_url = f"{servicenow_player_url}/{player_sys_id}"
            update_payload = {"u_goals": str(new_goals)}

            update_response = requests.put(
                update_url,
                auth=(servicenow_user, servicenow_pwd),
                headers=headers,
                json=update_payload
            )

            if update_response.status_code != 200:
                return jsonify({
                    'status': update_response.status_code,
                    'error': update_response.json()
                }), update_response.status_code

            # Return updated player data
            return jsonify(update_response.json()), 200

        else:  # If player does not exist, create a new player
            response = requests.post(
                servicenow_player_url,
                auth=(servicenow_user, servicenow_pwd),
                headers=headers,
                json={
                    "u_user": user_sys_id,  # Use the logged-in user's sys_id here
                    "u_name": u_name,
                    "u_goals": u_goals
                }
            )

            # Check for HTTP codes other than 201 (Created)
            if response.status_code != 201:
                return jsonify({
                    'status': response.status_code,
                    'headers': dict(response.headers),
                    'error_response': response.json()
                }), response.status_code

            # Decode the JSON response into a dictionary and return the data
            data = response.json()
            return jsonify(data), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_players', methods=['GET'])
@jwt_required()
def get_players():
    try:
        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()
        # Query ServiceNow to get players for the logged-in user
        query_url = f"{servicenow_player_url}?sysparm_query=u_user={user_sys_id}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if not players:
            return jsonify({"msg": "No players found for the logged-in user"}), 404

        # Extract name and goals, and sort by goals in descending order
        player_data = [{"u_name": player["u_name"], "u_goals": int(player["u_goals"])} for player in players]
        sorted_players = sorted(player_data, key=lambda x: x["u_goals"], reverse=True)

        return jsonify(sorted_players), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#ADD and GET WICKETS
@app.route('/add_wickets', methods=['POST'])
@jwt_required()
def add_wickets():
    try:
        # Get the JSON data from the request
        player_data = request.json

        if not player_data:
            return jsonify({"error": "No data provided"}), 400

        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()

        # Ensure the player data has the required fields
        u_name = player_data.get('u_name')
        u_wickets = player_data.get('u_wickets')

        if not u_name or not u_wickets:
            return jsonify({"error": "Missing required fields"}), 400

        # Query ServiceNow to check if the player already exists
        query_url = f"{servicenow_wkt_url}?sysparm_query=u_user={user_sys_id}^u_name={u_name}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if players:  # If player exists, add goals to the current goals
            player = players[0]
            player_sys_id = player['sys_id']
            current_wickets = player['u_wickets'] or 0  # Get the current goals, default to 0 if not available

            # Add the new goals to the current goals
            new_goals = int(current_wickets) + int(u_wickets)

            # Update player goals with the new total
            update_url = f"{servicenow_player_url}/{player_sys_id}"
            update_payload = {"u_wickets": str(u_wickets)}

            update_response = requests.put(
                update_url,
                auth=(servicenow_user, servicenow_pwd),
                headers=headers,
                json=update_payload
            )

            if update_response.status_code != 200:
                return jsonify({
                    'status': update_response.status_code,
                    'error': update_response.json()
                }), update_response.status_code

            # Return updated player data
            return jsonify(update_response.json()), 200

        else:  # If player does not exist, create a new player
            response = requests.post(
                servicenow_wkt_url,
                auth=(servicenow_user, servicenow_pwd),
                headers=headers,
                json={
                    "u_user": user_sys_id,  # Use the logged-in user's sys_id here
                    "u_name": u_name,
                    "u_wickets": u_wickets
                }
            )

            # Check for HTTP codes other than 201 (Created)
            if response.status_code != 201:
                return jsonify({
                    'status': response.status_code,
                    'headers': dict(response.headers),
                    'error_response': response.json()
                }), response.status_code

            # Decode the JSON response into a dictionary and return the data
            data = response.json()
            return jsonify(data), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_wickets', methods=['GET'])
@jwt_required()
def get_wickets():
    try:
        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()
        # Query ServiceNow to get players for the logged-in user
        query_url = f"{servicenow_wkt_url}?sysparm_query=u_user={user_sys_id}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if not players:
            return jsonify({"msg": "No players found for the logged-in user"}), 404

        # Extract name and goals, and sort by goals in descending order
        player_data = [{"u_name": player["u_name"], "u_wickets": int(player["u_wickets"])} for player in players]
        sorted_players = sorted(player_data, key=lambda x: x["u_wickets"], reverse=True)

        return jsonify(sorted_players), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#GET and ADD Highest Individual score
@app.route('/add_score', methods=['POST'])
@jwt_required()
def add_score():
    try:
        # Get the JSON data from the request
        player_data = request.json

        if not player_data:
            return jsonify({"error": "No data provided"}), 400

        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()

        # Ensure the player data has the required fields
        u_name = player_data.get('u_name')
        u_score = player_data.get('u_score')

        if not u_name or not u_score:
            return jsonify({"error": "Missing required fields"}), 400

        # Query ServiceNow to check if the player already exists

        response = requests.post(
            url,
            auth=(servicenow_user, servicenow_pwd),
            headers=headers,
            json={
                "u_user": user_sys_id,  # Use the logged-in user's sys_id here
                "u_name": u_name,
                "u_score": u_score
            }
        )

        # Check for HTTP codes other than 201 (Created)
        if response.status_code != 201:
            return jsonify({
                'status': response.status_code,
                'headers': dict(response.headers),
                'error_response': response.json()
            }), response.status_code

        # Decode the JSON response into a dictionary and return the data
        data = response.json()
        return jsonify(data), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_score', methods=['GET'])
@jwt_required()
def get_score():
    try:
        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()
        # Query ServiceNow to get players for the logged-in user
        query_url = f"{url}?sysparm_query=u_user={user_sys_id}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if not players:
            return jsonify({"msg": "No players found for the logged-in user"}), 404

        # Extract name and goals, and sort by goals in descending order
        player_data = [{"u_name": player["u_name"], "u_score": int(player["u_score"])} for player in players]
        sorted_players = sorted(player_data, key=lambda x: x["u_score"], reverse=True)

        return jsonify(sorted_players), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#GET and ADD Highest Team score
@app.route('/add_team_score', methods=['POST'])
@jwt_required()
def add_team_score():
    try:
        # Get the JSON data from the request
        player_data = request.json

        if not player_data:
            return jsonify({"error": "No data provided"}), 400

        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()

        # Ensure the player data has the required fields
        u_name = player_data.get('u_name')
        u_score = player_data.get('u_score')

        if not u_name or not u_score:
            return jsonify({"error": "Missing required fields"}), 400

        # Query ServiceNow to check if the player already exists

        response = requests.post(
            team_url,
            auth=(servicenow_user, servicenow_pwd),
            headers=headers,
            json={
                "u_user": user_sys_id,  # Use the logged-in user's sys_id here
                "u_name": u_name,
                "u_score": u_score
            }
        )

        # Check for HTTP codes other than 201 (Created)
        if response.status_code != 201:
            return jsonify({
                'status': response.status_code,
                'headers': dict(response.headers),
                'error_response': response.json()
            }), response.status_code

        # Decode the JSON response into a dictionary and return the data
        data = response.json()
        return jsonify(data), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_team_score', methods=['GET'])
@jwt_required()
def get_team_score():
    try:
        # Get the logged-in user's sys_id
        user_sys_id = get_jwt_identity()
        # Query ServiceNow to get players for the logged-in user
        query_url = f"{team_url}?sysparm_query=u_user={user_sys_id}"
        response = requests.get(query_url, auth=(servicenow_user, servicenow_pwd), headers=headers)

        if response.status_code != 200:
            return jsonify({
                'status': response.status_code,
                'error': response.json()
            }), response.status_code

        players = response.json().get('result')

        if not players:
            return jsonify({"msg": "No players found for the logged-in user"}), 404

        # Extract name and goals, and sort by goals in descending order
        player_data = [{"u_name": player["u_name"], "u_score": int(player["u_score"])} for player in players]
        sorted_players = sorted(player_data, key=lambda x: x["u_score"], reverse=True)

        return jsonify(sorted_players), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)
