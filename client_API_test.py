import requests

# Create a new user. Use JSON payload instead of form data
print("Will create a new user now")
user_data = {"username": "client4", "password": "password123", "email": "test@test.com"}
response = requests.post("http://localhost:8000/users/create", json=user_data)
print(response.json())  # Should print the new user info


# Log in to get the token
print("Will login with said user now")
login_data = {"username": "client4", "password": "password123"}
login_response = requests.post("http://localhost:8000/auth/login", data=login_data)
login_info = login_response.json()
print(login_info)  # Should print the token info
access_token = login_info['access_token']
refresh_token = login_info['refresh_token']

# Create a new job of type "generate_kraus"
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

# Ask the server for a job
print("Will request a job now")
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/jobs/request", headers=headers)
print(response)
print(response.json())  # Should print the dummy job info
id = response.json()["job_id"]

#Check the job status
print("Will check the job status now")
headers = {"Authorization": f"Bearer {access_token}"}
job_data = {"job_id": id}
response = requests.get(f"http://localhost:8000/jobs/status/", headers=headers, params=job_data)
print(response.json())  # Should print the job status info.

# Pause the job
print("Will pause the job now")
job_data = {"job_id": id}
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post("http://localhost:8000/jobs/pause", data=job_data, headers=headers)
print(response.json())  # Should print the job pause info

#Check the job status
print("Will check the job status now")
headers = {"Authorization": f"Bearer {access_token}"}
job_data = {"job_id": id}
response = requests.get(f"http://localhost:8000/jobs/status/", headers=headers, params=job_data)
print(response.json())  # Should print the job status info.

# Resume the job
print("Will resume the job now")
job_data = {"job_id": id}
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post("http://localhost:8000/jobs/resume", data=job_data, headers=headers)
print(response.json())  # Should print the job resume info

#Check the job status
print("Will check the job status now")
headers = {"Authorization": f"Bearer {access_token}"}
job_data = {"job_id": id}
response = requests.get(f"http://localhost:8000/jobs/status/", headers=headers, params=job_data)
print(response.json())  # Should print the job status info.

# Job is to create a kraus. Pretend we have completed the job. Create dummy out.dat file
print("Will pretend to complete the job now")
# Create a dummy file
with open("out.dat", "w") as f:
    f.write("This is a dummy file.")
# Step 1 for completing: upload files and update stats
# Request an upload link
print("Will request an upload link now")
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/files/request-upload", headers=headers)
print(response.json())  # Should print the upload link info
# Upload the file
print("Will upload the file now")
upload_link = response.json()["upload_url"]
upload_link = "http://localhost:8000/" + upload_link
print("Upload link:", upload_link)
files = {"file": open("out.dat", "rb")}
headers = {"Authorization": f"Bearer {access_token}"}
data = {"job_id": str(id), "file_type": "kraus"}
response = requests.post(upload_link, files=files, headers=headers, data=data)
print(response.json())  # Should print the file upload info
# update the iterations to 1000
print("Will update the iterations now")
job_data = {"job_id": str(id), "num_iterations": 1000}
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post("http://localhost:8000/jobs/update-iterations", data=job_data, headers=headers)
print(response.json())  # Should print the job iteration info
# Step 2: mark the job as finished
print("Will mark the job as finished now")
job_data = {"job_id": str(id)}
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post("http://localhost:8000/jobs/complete", data=job_data, headers=headers)
print(response.json())  # Should print the job completion info
#Check the job status
print("Will check the job status now")
headers = {"Authorization": f"Bearer {access_token}"}
job_data = {"job_id": id}
response = requests.get(f"http://localhost:8000/jobs/status/", headers=headers, params=job_data)
print(response.json())  # Should print the job status info.