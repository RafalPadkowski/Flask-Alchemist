import fileinput
import pathlib
from math import ceil
from pprint import pprint

import click
import sqlalchemy as sa
import sqlalchemy.orm as so
from alembic import command as alembic_command
from alembic.config import Config
from flask import abort, request


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

        self.pagination_per_page = None
        self.Pagination = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.Session.configure(
            bind=sa.create_engine(url=app.config["DATABASE_URL"], echo=False)
        )

        self.pagination_per_page = app.config.get("PAGINATION_PER_PAGE", 10)
        self.Pagination = self.get_pagination()

        @app.cli.command("db")
        @click.argument("command")
        def db_command(command):
            """Possible commands:

            \b
            init - initialize migrations
            migrate - create a new migration script
            upgrade - upgrade database

            """

            alembic_cfg = Config("alembic.ini")

            match command:
                case "init":
                    alembic_command.init(alembic_cfg, "migrations")

                    backup_file_path = (
                        pathlib.Path("migrations").absolute() / "env.py.bak"
                    )
                    print(f"  Creating backup file '{backup_file_path}' ...", end="  ")

                    with fileinput.FileInput(
                        "migrations/env.py", inplace=True, backup=".bak"
                    ) as f:
                        line = f.readline()
                        print("from flask_alchemist import Model", end="\n")
                        print("import app.models", end="\n")
                        print("from instance.config import DATABASE_URL", end="\n")
                        print(line, end="")

                        for line in f:
                            if "target_metadata = None" in line:
                                print(line.rstrip().replace("None", "Model.metadata"))
                                print(
                                    "config.set_main_option"
                                    '("sqlalchemy.url", DATABASE_URL)'
                                )
                            elif (
                                "connection=connection, target_metadata=target_metadata"
                                in line
                            ):
                                print(line.rstrip() + ", render_as_batch=True")
                            else:
                                print(line, end="")

                    print("done")

                case "migrate":
                    alembic_command.revision(alembic_cfg, autogenerate=True)

                case "upgrade":
                    alembic_command.upgrade(alembic_cfg, "head")

    def get_pagination(self):
        db_self = self

        class Pagination:
            def __init__(self, query):
                try:
                    self.page = int(request.args.get("page", 1))
                except ValueError:
                    abort(404)

                self.per_page = db_self.pagination_per_page

                q_count = sa.select(sa.func.count()).select_from(query)

                with db_self.Session() as db_session:
                    self.total = db_session.scalar(q_count)

                self.pages = ceil(self.total / self.per_page)

                if self.pages:
                    if not 1 <= self.page <= self.pages:
                        abort(404)

                    offset = (self.page - 1) * self.per_page

                    with db_self.Session() as db_session:
                        self.items = db_session.scalars(
                            query.limit(self.per_page).offset(offset)
                        ).all()

                    self.first = offset + 1

                    if self.page != self.pages:
                        self.last = offset + self.per_page
                    else:
                        self.last = self.total
                else:
                    if self.page != 1:
                        abort(404)

                    self.items = []
                    self.first = self.last = 0

                self.prev_num = self.page - 1
                self.next_num = self.page + 1

            @property
            def has_prev(self):
                return self.prev_num >= 1

            @property
            def has_next(self):
                return self.next_num <= self.pages

            def __iter__(self):
                yield from self.items

            def iter_pages(self):
                if not self.pages:
                    return

                on_edges = 2
                on_each_side = 3

                left_begin = 1
                left_end = on_edges

                for i in range(left_begin, left_end + 1):
                    yield i
                    if i >= self.pages:
                        return

                left_end += 1

                mid_begin = self.page - on_each_side
                mid_end = self.page + on_each_side

                if mid_begin > left_end:
                    yield None
                else:
                    mid_begin = left_end

                for i in range(mid_begin, mid_end + 1):
                    yield i
                    if i >= self.pages:
                        return

                mid_end += 1

                right_begin = self.pages - on_edges + 1
                right_end = self.pages

                if right_begin > mid_end:
                    yield None
                else:
                    right_begin = mid_end

                for i in range(right_begin, right_end + 1):
                    yield i
                    if i >= self.pages:
                        return

        return Pagination

    def __getattr__(self, name):
        for mod in (sa, so):
            if hasattr(mod, name):
                return getattr(mod, name)

        raise AttributeError(name)
