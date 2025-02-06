import requests

# Check the status without logging in
print("Will request the status without logging in")
response = requests.get("http://localhost:8000/")
print(response.json())  # Should print the dummy status info
print("\n")

# Create a new user. Use JSON payload instead of form data
print("Will create a new user now")
user_data = {"username": "client4", "password": "password123", "email": "test@test.com"}
response = requests.post("http://localhost:8000/users/signup", json=user_data)
print(response.json())  # Should print the new user info
print("\n")


# First, log in to get the token
print("Will login with said user now")
login_data = {"username": "client4", "password": "password123"}
login_response = requests.post("http://localhost:8000/auth/login", data=login_data)
login_info = login_response.json()
print(login_info)  # Should print the token info
access_token = login_info['access_token']
refresh_token = login_info['refresh_token']
print("\n")

# Now, refresh the token
print("Will refresh now")
refresh_headers = {"refresh": refresh_token}
refresh_response = requests.post("http://localhost:8000/auth/refresh", headers=refresh_headers)
refresh_info = refresh_response.json()
print(refresh_info)  # Should print the new token info
access_token_2 = refresh_info['access_token']
refresh_token_2 = refresh_info['refresh_token']
print("access_token_2:", access_token_2)
print("refresh_token_2:", refresh_token_2)
print("\n\n\n\n")

# Try using the old refresh token again
print("Will try to refresh again with the old refresh token")
print("Token used:", refresh_token)
refresh_headers = {"refresh": refresh_token}
refresh_response = requests.post("http://localhost:8000/auth/refresh", headers=refresh_headers)
print(refresh_response.json())  # Should print an error
print("\n\n\n\n")


# Now, request the status using the new access token
print("Will request the status now, using the new access token")
print("Token used:", access_token_2)
print("New refresh token:", refresh_token_2)
headers = {"Authorization": f"Bearer {access_token_2}"}
response = requests.get("http://localhost:8000/", headers=headers)
print(response.json())  # Should print the dummy status info
print("\n\n\n\n")

