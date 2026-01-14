format:
	ruff format .

fix:
	ruff check --fix .

docker_build:
	docker compose up -d --build

run_scheduler:
	python3 scheduler.py

run_bot:
	python3 bot.py

init_db:
	python3 init_db.py

refresh_db:
	python3 refresh_db.py
