# Flask-Alchemist

Flask extension for working with SQLAlchemy.

It can be used as an alternative for Flask-SQLAlchemy.

Instead of the scoped session tied to a thread you can instantiate database session
on demand with a context manager. The advantage is that when the Flask application handles a request you can precisely control when the session starts and ends.

There is also a Model class with modified MetaData configuration which tells SQLAlchemy how to name indexes and constraints in a database.
You can subclass it to define your own model classes.

The Model class provides also show_column method to display information about columns defined in a model (it helps when you want to create 
database objects in the Flask shell).

## Installation

```bash
$ pip install Flask-Alchemist
```

## Usage

First create the `db` object:

```python
from flask_alchemist import Alchemist
db = Alchemist()
```

Then initialize it using init_app method:

```python
db.init_app(app)  # app is your Flask app instance
```
The Flask app config should have `DATABASE_URL` key. That is a connection string that tells SQLAlchemy what database to connect to.

Using the `db` object you can create database session on demand in your views:

```python
with db.Session() as db_session:
    user = db_session.get(User, obj_id)
```

The session is closed when the context manager block ends.

When you want to modify database you can combine two context managers:

```python
with db.Session() as db_session:
    with db_session.begin():
        db_session.add(obj)
```

or

```python
with db.Session() as db_session, db_session.begin():
    db_session.add(obj)
```

The session automatically commits (inner context manager) and closes (outer context manager) at the end. If an error occurs inside the inner context manager the session is rolled back.

After defining your User model class you can inspect it in the Flask shell:

```python
>>> User.show_columns()
Column('id', Integer(), table=<users>, primary_key=True, nullable=False)
Column('username', String(length=64), table=<users>, nullable=False)
Column('password_hash', String(length=162), table=<users>)
Column('first_name', String(length=64), table=<users>, nullable=False)
Column('last_name', String(length=64), table=<users>, nullable=False)
Column('email', String(length=64), table=<users>, nullable=False, default=ScalarElementColumnDefault(''))
Column('active', Boolean(), table=<users>, nullable=False, default=ScalarElementColumnDefault(True))
```

## Other features

Alchemist object can be used as a proxy for any attribute of the SQLAlchemy Core and the SQLAlchemy ORM.
For example when making SQL queries you can use db.select instead of importing this from SQLAlchemy.


## License

`Flask-Alchemist` was created by Rafal Padkowski. It is licensed under the terms
of the MIT license.
