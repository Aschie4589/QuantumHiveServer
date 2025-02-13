from redis import Redis

# Redis Settings
# Connect to Redis
# TODO: Can we make this more secure? Redis is exposed to the internet.
redis_client = Redis(host="redis", port=6379, db=0)