# Setup swarming
docker swarm init

# Check if the docker secret is already created. If it is, skip the creation.
if [ $(docker secret ls | grep db_password | wc -l) -gt 0 ]; then
    echo "DB secret already exists. Skipping creation."
    exit 0
else
    echo "DB secret does not exist. Creating secret."
    # Generate a random 256-byte secret. TODO: Change this to a more secure method.
    SECRET=$(openssl rand -base64 32)

    # Create Docker secret for the PostgreSQL password.
    # This secret will be used in the docker-compose.yml file, and will make communication between the API and the db more secure.
    echo $SECRET | docker secret create db_password -

fi

# Do the same for JWT secret
if [ $(docker secret ls | grep jwt_secret | wc -l) -gt 0 ]; then
    echo "JWT secret already exists. Skipping creation."
    exit 0
else
    echo "JWT secret does not exist. Creating secret."
    # Generate a random 256-byte secret. TODO: Change this to a more secure method.
    SECRET=$(openssl rand -base64 32)

    # Create Docker secret for the JWT secret.
    # This secret will be used in the docker-compose.yml file, and will make communication between the API and the db more secure.
    echo $SECRET | docker secret create jwt_secret -

fi

docker secret ls

# Build the images
docker build -t quantumhive/uvicorn-server .

# Deploy the stack
docker stack deploy -c docker-compose.yml quantum_hive_stack

# Check that postgres is running. If so, change the password.
# Note that the pw needs to be loaded from the secret within the system!
if docker ps --filter "name=quantum_hive_stack_db" --format '{{.ID}}' | grep -q .; then
    echo "Postgres is running. Changing password."
    # PW needs to be read in docker container
    # docker exec to run a command in a running container and read the secret
    TRIES=5
    while [ $TRIES -gt 0 ]; do
        PROCESS=$(docker ps -q --filter name=quantum_hive_stack_db)
        if [ -n "$PROCESS" ]; then
            STATUS=$(docker inspect --format='{{.State.Status}}' $PROCESS)
            if [ "$STATUS" = "running" ]; then
                break
            fi
        fi
        echo "Waiting for Postgres container to be ready..."
        sleep 3
        ((TRIES--))
    done
    docker exec -it $PROCESS psql -U quantumhive -c "ALTER USER quantumhive WITH PASSWORD '$(docker exec -i $PROCESS cat /run/secrets/db_password)';"
else
    echo "Postgres is not running. Skipping password change."
fi
