#!/usr/bin/env sh
# Copies a local SQLite database file into the `db` Docker named volume used by
# the `app`/`web` services in docker-compose.yml, replacing whatever is there.
#
# This is useful to load a copy of a database (e.g. one taken from another
# environment) into the Dockerised deployment, whether running in development
# or production-like mode.
#
# Usage:
#   scripts/load_db.sh [path/to/db.sqlite3]
#
# If no path is given, it defaults to db/db.sqlite3 in the project root.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

SOURCE_DB="${1:-$PROJECT_DIR/db/db.sqlite3}"

if [ ! -f "$SOURCE_DB" ]; then
  echo "Error: source database file not found: $SOURCE_DB" >&2
  exit 1
fi

# Resolve to an absolute path, since it is bind-mounted into a container that
# will be run from the project directory.
case "$SOURCE_DB" in
  /*) ;;
  *) SOURCE_DB="$(CDPATH= cd -- "$(dirname -- "$SOURCE_DB")" && pwd)/$(basename -- "$SOURCE_DB")" ;;
esac

cd "$PROJECT_DIR"

echo "Stopping services that may be using the database..."
docker compose stop app web

echo "Copying '$SOURCE_DB' into the 'db' volume..."
docker compose run --rm --no-deps \
  --volume "$SOURCE_DB:/tmp/source_db.sqlite3:ro" \
  app \
  sh -c "cp /tmp/source_db.sqlite3 db/db.sqlite3 && chown nobody:nogroup db/db.sqlite3"

echo "Done. The 'db' volume now contains the contents of '$SOURCE_DB'."
echo "Restart services as needed, e.g.:"
echo "  docker compose up"
echo "  docker compose --profile production up web proxy"
