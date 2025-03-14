-- Print message
RAISE NOTICE 'Creating database and tables...';

-- Create database
CREATE DATABASE quantumhive;

-- Connect to the new database 'quantumhive' (after creating it)
\c quantumhive;

-- Create user if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'quantumhive') THEN
        CREATE USER quantumhive WITH ENCRYPTED PASSWORD 'tmppw';
    -- Else, print a message
    ELSE
        RAISE NOTICE 'User quantumhive already exists';
    END IF;
END $$;

-- Grant all privileges to the quantumhive user
GRANT ALL PRIVILEGES ON DATABASE quantumhive TO quantumhive;


-- Create the users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_type TEXT NOT NULL CHECK (job_type IN ('minimize', 'generate_kraus', 'generate_vector')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')),
    input_data JSONB,  -- Store job parameters in structured format
    kraus_operator TEXT,  -- File path or reference
    vector TEXT,  -- Store initial or final vector (or reference)
    entropy DOUBLE PRECISION NOT NULL DEFAULT -1.0,  -- Store the entropy of the final vector, if applicable
    num_iterations INTEGER DEFAULT 0,  -- Track how many iterations were run
    time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_started TIMESTAMP,
    time_finished TIMESTAMP,
    last_update TIMESTAMP,
    worker_id TEXT,  -- Assigned worker (nullable initially)
    channel_id INTEGER, -- Reference to the channel, null if not assigned
    priority INTEGER DEFAULT 1
);

CREATE TABLE files (
    id VARCHAR(8) PRIMARY KEY,
    type VARCHAR(50) NOT NULL CHECK (type IN ('kraus', 'vector')),
    full_path VARCHAR(255) NOT NULL UNIQUE
);


-- Create the channels table
CREATE TABLE channels (
    id SERIAL PRIMARY KEY,
    kraus_id VARCHAR(8) DEFAULT NULL,
    best_moe DOUBLE PRECISION NOT NULL DEFAULT -1.0,
    best_entropy_vector_id VARCHAR(8) DEFAULT NULL,
    minimization_attempts INT NOT NULL DEFAULT 100,
    runs_spawned INT NOT NULL DEFAULT 0,
    runs_completed INT NOT NULL DEFAULT 0,
    input_dimension INT NOT NULL,
    output_dimension INT NOT NULL,
    num_kraus INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    CONSTRAINT status_check CHECK (status IN ('created', 'generating', 'minimizing', 'paused', 'completed'))
);