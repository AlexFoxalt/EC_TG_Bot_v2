MSG ?= auto

format:
	ruff format .

fix:
	ruff check --fix .

docker_build:
	docker compose up -d --build

docker_stop:
	docker compose stop

run_scheduler:
	python3 entrypoints/scheduler.py

run_bot:
	python3 entrypoints/bot.py

run_maintenance:
	python3 entrypoints/maintenance.py

run_pi_client:
	python3 entrypoints/start_pi_client.py

run_pi_server:
	python3 entrypoints/start_pi_server.py

init_db:
	python3 entrypoints/init_db.py

refresh_db:
	python3 entrypoints/refresh_db.py

migrations:
	alembic revision --autogenerate -m "$(MSG)"

migrate:
	alembic upgrade head

downgrade:
	alembic downgrade -1

logs_compact:
	docker compose logs -f bot scheduler pi_server

logs_all:
	docker compose logs -f

logs-last-100:
	docker compose logs --tail=100

systemctl_logs:
	journalctl -n 50 -u pi-client

systemctl_restart:
	systemctl restart pi-client
