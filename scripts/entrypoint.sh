#!/bin/sh
set -e

alembic upgrade head
python -m app.initial_data

exec "$@"
