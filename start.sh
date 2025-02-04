# Setup swarming
docker swarm init

# Generate a random 256-byte secret. TODO: Change this to a more secure method.
SECRET=$(openssl rand -base64 256)

# Create Docker secret for the PostgreSQL password.
# This secret will be used in the docker-compose.yml file, and will make communication between the API and the db more secure.
echo $SECRET | docker secret create db_password -

docker secret ls

# Build the images
docker build -t quantumhive/uvicorn-server .

# Deploy the stack
docker stack deploy -c docker-compose.yml quantum_hive_stack