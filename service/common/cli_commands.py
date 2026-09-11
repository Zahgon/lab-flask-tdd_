"""
CLI Command Extensions
"""
import click

from service import config
from service.models import db


######################################################################
# Command to force tables to be rebuilt
# Usage:
#   db-create
######################################################################
@click.command("db-create")
def db_create():
    """
    Recreates a local database. You probably should not use this on
    production. ;-)
    """
    if db.engine is None:
        db.init_engine(config.DATABASE_URI)
    db.drop_all()
    db.create_all()
    db.session.commit()


if __name__ == "__main__":  # pragma: no cover
    db_create()  # pylint: disable=no-value-for-parameter
