# Start the Docker Compose setup
up:
	docker compose up

# Stop the Docker Compose setup
down:
	docker compose down

# All starting commands
start: up

# All stopping commands
stop: down