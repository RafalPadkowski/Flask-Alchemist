from pprint import pprint

import sqlalchemy as sa
import sqlalchemy.orm as so


class Model(so.DeclarativeBase):
    metadata = sa.MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    @classmethod
    def show_columns(cls):
        for column in list(cls.__table__.columns):
            pprint(column)


class Alchemist:
    def __init__(self, app=None):
        self.Model = Model
        self.Session = so.sessionmaker()

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.Session.configure(
            bind=sa.create_engine(url=app.config["DATABASE_URL"], echo=False)
        )

    def __getattr__(self, name):
        for mod in (sa, so):
            if hasattr(mod, name):
                return getattr(mod, name)

        raise AttributeError(name)
