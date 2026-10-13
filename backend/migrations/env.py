from alembic import context
from sqlalchemy import create_engine

from app.deps import engine as app_engine
from app.models import Model

# Not the app's engine: its 2s statement timeout would cancel slow migrations.
engine = create_engine(app_engine.url)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Model.metadata)
    with context.begin_transaction():
        context.run_migrations()
