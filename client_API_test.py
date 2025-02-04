import requests

# First, log in to get the token
print("Will login now")
login_data = {"username": "client", "password": "password123"}
login_response = requests.post("http://localhost:8000/login", data=login_data)
login_info = login_response.json()
print(login_info)  # Should print the token info
access_token = login_info['access_token']
refresh_token = login_info['refresh_token']
print("\n\n\n\n")

# Now, refresh the token
print("Will refresh now")
refresh_headers = {"refresh": refresh_token}
refresh_response = requests.post("http://localhost:8000/refresh", headers=refresh_headers)
refresh_info = refresh_response.json()
print(refresh_info)  # Should print the new token info
access_token_2 = refresh_info['access_token']
refresh_token_2 = refresh_info['refresh_token']

print("\n\n\n\n")

# Try using the old refresh token again
print("Will try to refresh again with the old refresh token")
refresh_headers = {"refresh": refresh_token}
refresh_response = requests.post("http://localhost:8000/refresh", headers=refresh_headers)
print(refresh_response.json())  # Should print an error
print("\n\n\n\n")


# Now, request the status using the new access token
print("Will request the status now, using the new access token")
headers = {"Authorization": f"Bearer {access_token_2}"}
response = requests.get("http://localhost:8000/status", headers=headers)
print(response.json())  # Should print the dummy status info
print("\n\n\n\n")

# Now, request the status again using the new access token
headers = {"Authorization": f"Bearer {access_token_2}"}
response = requests.get("http://localhost:8000/status", headers=headers)
print(response.json())  # Should print the dummy status info
print("\n\n\n\n")
