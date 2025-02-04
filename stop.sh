# Remove persistent volumes (for testing)
docker compose down -v
# Stop the stack
docker stack rm quantum_hive_stack
# Leave the swarm
docker swarm leave --force