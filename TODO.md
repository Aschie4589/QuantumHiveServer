## IMPORTANT SECURITY STUFF

- Authentication with proper pw database and hashing
    - Rate limiting?
- Token database needs to be protected
    - Token rotation?
- HTTPS

## FUNCTIONALITY

- API endpoints for
    - Asking for a job
    - Downloading kraus operators
    - Downloading vectors
    - Uploading vectors
    - Uploading kraus
    - Seeing stats for the current channel
    - Seeing stats for all channels
    - Pausing job
    - Resuming job
    - Cancelling job (when quitting)

- Job format
    - Specify the JSON response when asking for a job. Like {"job":"minimize", "mode": "singleshot", "kraus": "url"}, or {"job": "generate_kraus", "d", 100, "N", 1024, "mode":"haar"}
    - Make sure you can't get new job before having finsihed current one!

- Channels database
    - Stores info about channels:
        - Kraus operators used (filename/path? if mounted where?)
        - Current best MOE found
        - If new jobs need to be spawned
        - Total number of runs completed
        - Number of runs that are pending


- Jobs database
    - Stores all jobs info. That is:
        - Kraus operators used
        - If job is running, paused, needs allocation or is finished
        - current best vector found (either coming from "/save" endopint, or just the starting vector)
        - Time started
        - Time finished, if relevant
        - Time of last update from client (to determine if job is running)
        - User last allocated to the task/currently minimizing (username?)

- Users database
    - Stores the allowed usernames and the corresponding hashed passwords, and what role these users have (admin or user?)

- Login database?
    - Store login attempts

- Log database
    - Store event log of all that happens?

- Tokens database
    - Keeps track of the revoked tokens

# Wishlist

- Database backups
- Proper logging system
- UI dashboard?
- 