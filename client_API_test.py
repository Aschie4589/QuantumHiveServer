import requests

#api_url = "http://localhost:8000"
api_url = "http://apiv1.quantum-hive.com"


# Create a new user. Use JSON payload instead of form data
print("Will create a new user now")
user_data = {"username": "client", "password": "password", "email": "admin@test.com"}
response = requests.post(f"{api_url}/users/create", json=user_data)
print(response.json())  # Should print the new user info


# Log in to get the token
print("Will login with said user now")
login_data = {"username": "admin", "password": "admin"}
login_response = requests.post(f"{api_url}/auth/login", data=login_data)
login_info = login_response.json()
print(login_info)  # Should print the token info
access_token = login_info['access_token']
refresh_token = login_info['refresh_token']

if True:
    # Create channel
    print("Will create a channel now")
    channel_data = {"input_dimension": 1024, "output_dimension": 1024, "num_kraus": 24, "method": "haar"}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(f"{api_url}/channels/create", data=channel_data, headers=headers)
    print(response)  # Should print the channel creation info

    
if False:
    # List channels
    print("Will list the channels now")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("http://localhost:8000/channels/list", headers=headers)
    print(response.json())  # Should print the channel list

    # get id from response
    channel_id = response.json()[0]["id"]

    # Update minimization attempts
    print("Will update minimization attempts now")
    min_attempts_data = {"channel_id": channel_id, "attempts": 100}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post("http://localhost:8000/channels/update-minimization-attempts", data=min_attempts_data, headers=headers)
    print(response.json())  # Should print the success message




    # Ask the server for a job
    print("Will request a job now")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("http://localhost:8000/jobs/request", headers=headers)
    print(response)
    print(response.json())  # Should print the dummy job info


    if response.status_code == 200:
        # Have received a job. Depending on job type, pretend to have completed the job.
        id = response.json()["job_id"]
        typ = response.json()["job_type"]

        if typ == "generate_kraus":
            print("Asked to generate kraus")
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
            print(response.json())
            # Upload the file
            print("Will upload the file now")
            upload_link = response.json()["upload_url"]
            upload_link = "http://localhost:8000/" + upload_link
            print("Upload link:", upload_link)
            files = {"file": open("out.dat", "rb")}
            headers = {"Authorization": f"Bearer {access_token}"}
            data = {"job_id": str(id), "file_type": "kraus"}
            response = requests.post(upload_link, files=files, headers=headers, data=data)
            print(response.json())
            # Step 2: mark the job as finished
            print("Will mark the job as finished now")
            job_data = {"job_id": str(id)}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post("http://localhost:8000/jobs/complete", data=job_data, headers=headers)
            print(response.json())

        elif typ == "generate_vector":
            print("Asked to generate vector")
            # Job is to create a vector. Pretend we have completed the job. Create dummy out.dat file
            print("Will pretend to complete the job now")
            # Create a dummy file
            with open("out.dat", "w") as f:
                f.write("This is a dummy file.")
            # Step 1 for completing: upload files and update stats
            # Request an upload link
            print("Will request an upload link now")
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get("http://localhost:8000/files/request-upload", headers=headers)
            print(response.json())
            # Upload the file
            print("Will upload the file now")
            upload_link = response.json()["upload_url"]
            upload_link = "http://localhost:8000/" + upload_link
            print("Upload link:", upload_link)
            files = {"file": open("out.dat", "rb")}
            headers = {"Authorization": f"Bearer {access_token}"}
            data = {"job_id": str(id), "file_type": "vector"}
            response = requests.post(upload_link, files=files, headers=headers, data=data)
            print(response.json())
            # Step 2: mark the job as finished
            print("Will mark the job as finished now")
            job_data = {"job_id": str(id)}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post("http://localhost:8000/jobs/complete", data=job_data, headers=headers)
            print(response.json())

        elif typ == "minimize":
            print("Asked to minimize")
            # Job is to minimize. In theory we would have to run minimization, upload a vector and update the moe.
            # None of the steps are actually necessary! Just pretend to have completed the job.
            print("Will pretend to complete the job now")
            # Just complete
            job_data = {"job_id": str(id)}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post("http://localhost:8000/jobs/complete", data=job_data, headers=headers)
            print(response.json())


