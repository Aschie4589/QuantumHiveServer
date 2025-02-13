import requests

# Check the status without logging in
print("Will request the status without logging in")
response = requests.get("http://localhost:8000/")
print(response.json())  # Should print the dummy status info
print("\n")



# Create a new user. Use JSON payload instead of form data
print("Will create a new user now")
user_data = {"username": "client4", "password": "password123", "email": "test@test.com"}
response = requests.post("http://localhost:8000/users/create", json=user_data)
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

# now, create a new job of type "generate_kraus"
print("Will create a new job now")
job_data = {
    "job_type": "generate_kraus",
    "input_data": {"N": 100, "d": 20},
    "kraus_operator": "",
    "vector": ""
    }

headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post("http://localhost:8000/jobs/create", json=job_data, headers=headers)
print(response.json())  # Should print the new job info

# Get job
print("Will request a job now")
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/jobs/request", headers=headers)
print(response)
print(response.json())  # Should print the dummy job info
id = response.json()["job_id"]
# Pretend we have completed the job. Create dummy out.dat file
print("Will pretend to complete the job now")
# Create a dummy file
with open("out.dat", "w") as f:
    f.write("This is a dummy file.")

# Request an upload link
print("Will request an upload link now")
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/files/request-upload", headers=headers)
print(response.json())  # Should print the upload link info

# Upload the file
print("Will upload the file now")
upload_link = response.json()["upload_url"]
#append localhost
upload_link = "http://localhost:8000/" + upload_link
print("Upload link:", upload_link)
files = {"file": open("out.dat", "rb")}
headers = {"Authorization": f"Bearer {access_token}"}
# use localhost for testing
data = {"job_id": str(id), "file_type": "kraus"}
response = requests.post(upload_link, files=files, headers=headers, data=data)
print(response.json())  # Should print the file upload info
print("\n")


# Next try to download it again.
print("Will request the download link now")
headers = {"Authorization": f"Bearer {access_token}"}   
# Need the id of the file to download

response = requests.get("http://localhost:8000/files/request-download", headers=headers)
print(response.json())  # Should print the download link info

