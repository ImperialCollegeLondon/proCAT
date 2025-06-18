"""This module sets up a Huey instance using SQLite as the storage backend."""

from huey import SqliteHuey

huey = SqliteHuey()
