default: docker-run

down:
	docker-compose down

migrate:
	docker-compose run --rm backend-tables python manage.py migrate

cli:
	docker-compose run --rm backend-tables bash

test:
	docker-compose run --rm backend-tables python manage.py test

check-for-unapplied-migrations:
	docker-compose run --rm  backend-tables python manage.py makemigrations --check --dry-run

makemigrations:
	docker-compose run --rm backend-tables python manage.py makemigrations

docker-build:
	docker-compose build

docker-run:
	docker-compose up