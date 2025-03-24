# Detect docker
if ! [ -x "$(command -v docker)" ]; then
    echo "Docker is not installed. Please install Docker before running this script."
    exit 1
fi

# Setup swarming
docker swarm init

# Check if the docker secret is already created. If it is, skip the creation.
if [ $(docker secret ls | grep db_password | wc -l) -gt 0 ]; then
    echo "DB secret already exists. Skipping creation."
    exit 0
else
    echo "DB secret does not exist. Creating secret:"
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
    echo "JWT secret does not exist. Creating secret:"
    # Generate a random 256-byte secret. TODO: Change this to a more secure method.
    SECRET=$(openssl rand -base64 32)

    # Create Docker secret for the JWT secret.
    # This secret will be used in the docker-compose.yml file, and will make communication between the API and the db more secure.
    echo $SECRET | docker secret create jwt_secret -

fi


# Check if the image exists
IMAGE_NAME="quantumhive/uvicorn-server"

if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Uvicorn image $IMAGE_NAME not found. Building the image..."
    docker build -t $IMAGE_NAME .
    echo "Uvicorn image built successfully."
else
    echo "Uvicorn image ($IMAGE_NAME) already exists. Checking for updates..."

    # Check if local files changed since the last build
    if [[ -f .docker_last_build ]]; then
        CHANGED_FILES=$(find ./app -type f -newer .docker_last_build)
    else
        CHANGED_FILES="force_rebuild"  # First-time force rebuild
    fi

    if [[ ! -z "$CHANGED_FILES" ]]; then
        echo "Changes detected in local files. Rebuilding the image..."
        docker build -t $IMAGE_NAME .
        touch .docker_last_build  # Update the timestamp
    else
        echo "No changes detected. Skipping build."
    fi
fi

# Deploy the stack
docker stack deploy -c docker-compose.yml quantum_hive_stack

# Check that postgres is running. If so, change the password.
# Note that the pw needs to be loaded from the secret within the system!
TRIES=5
while [ $TRIES -gt 0 ]; do
    PROCESS=$(docker ps -q --filter name=quantum_hive_stack_db)
    
    if [ -n "$PROCESS" ]; then
        STATUS=$(docker inspect --format='{{.State.Status}}' $PROCESS)
        if [ "$STATUS" = "running" ]; then
            echo "Postgres container found and running. Changing password."
            docker exec -it $PROCESS psql -U quantumhive -c "ALTER USER quantumhive WITH PASSWORD '$(docker exec -i $PROCESS cat /run/secrets/db_password)';"
            exit 0
        fi
    fi
    
    echo "Postgres container not found or not running. Retrying in 3 seconds... ($TRIES tries left)"
    sleep 3
    ((TRIES--))
done

echo "Postgres is not running or could not be found after multiple attempts. Skipping password change: the server will not be able to connect to the database. Will shut down the stack."

# Run ./stop
#./stop.sh
exit 1
