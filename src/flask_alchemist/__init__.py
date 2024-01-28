from math import ceil
from pprint import pprint

import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import Blueprint, abort, request


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

        blueprint = Blueprint(
            "db",
            __name__,
            template_folder="templates/"
            + app.config.get("TEMPLATE_MODE", "bootstrap5"),
        )

        app.register_blueprint(blueprint)

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

                pages_end = self.pages + 1

                left_end = min(1 + on_edges, pages_end)
                yield from range(1, left_end)

                if left_end == pages_end:
                    return

                mid_start = max(left_end, self.page - on_each_side)
                mid_end = min(self.page + on_each_side + 1, pages_end)

                if mid_start - left_end > 0:
                    yield None

                yield from range(mid_start, mid_end)

                if mid_end == pages_end:
                    return

                right_start = max(mid_end, pages_end - on_edges)

                if right_start - mid_end > 0:
                    yield None

                yield from range(right_start, pages_end)

        return Pagination

    def __getattr__(self, name):
        for mod in (sa, so):
            if hasattr(mod, name):
                return getattr(mod, name)

        raise AttributeError(name)
