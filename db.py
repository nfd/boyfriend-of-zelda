# https://flask.palletsprojects.com/en/1.1.x/tutorial/database/
from contextlib import contextmanager
import datetime
import getpass
import sqlite3
import uuid
import xml.parsers.expat
import sys

import bcrypt
import click
from flask import current_app, g
from flask.cli import with_appcontext

class Tags(list):
    pass

def adapt_tags(tags):
    return ';' + ';'.join(tags) + ';'

def convert_tags(s):
    s = s.decode()[1:-1]
    return Tags(s.split(';') if s else [])

sqlite3.register_adapter(Tags, adapt_tags)
sqlite3.register_converter("tags", convert_tags)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@contextmanager
def db_cursor():
    db = get_db()
    cursor = db.cursor()
    yield cursor
    db.commit()
    cursor.close()

def _convert_bookmark_dict_value(cursor, key, value):
    if key == 'shared':
        return 1 if value == 'yes' else 0
    return value

def _prepare_bookmark_add_edit(cursor, bookmark_dict, dict_keys):
    assert bookmark_dict.get('href')

    keys = []
    values = []
    for key in dict_keys:
        if key in bookmark_dict:
            keys.append(key)
            values.append(_convert_bookmark_dict_value(cursor, key, bookmark_dict[key]))

    return keys, values

def _new_bookmark(cursor, bookmark_dict, allow_big_id=False):
    if not allow_big_id and bookmark_dict.get('big_id'):
        raise ValueError()

    bookmark_dict['big_id'] = str(uuid.uuid4())

    new_bookmark_keys = ('owner', 'created', 'href', 'description', 'extended', 'big_id', 'tags', 'shared')
    keys, values = _prepare_bookmark_add_edit(cursor, bookmark_dict, new_bookmark_keys)

    unknowns = ', '.join(['?'] * len(values))
    cursor.execute(f"INSERT INTO bookmarks({', '.join(keys)}) VALUES ({unknowns})", values)

def _update_bookmark(cursor, bookmark_dict):
    if not bookmark_dict.get('big_id'):
        raise ValueError()

    update_keys = ('href', 'description', 'extended', 'tags', 'shared')
    keys, values = _prepare_bookmark_add_edit(cursor, bookmark_dict, update_keys)

    updates = ', '.join(f'{key} = ?' for key, value in zip(keys, values))
    cursor.execute(f"UPDATE bookmarks SET {updates} WHERE big_id=?", values + [bookmark_dict['big_id']])

def add_edit_bookmark(bookmark_dict):
    bookmark_dict = bookmark_dict.copy()
    with db_cursor() as cursor:
        if bookmark_dict.get('big_id'):
            _update_bookmark(cursor, bookmark_dict)
        else:
            _new_bookmark(cursor, bookmark_dict)

    return bookmark_dict['big_id']

def delete_bookmark(big_id):
    with db_cursor() as cursor:
        cursor.execute('DELETE FROM bookmarks WHERE big_id=?', (big_id,))

def get_bookmarks(limit, offset=0, search=None, username=None, include_private=False):
    if username is None:
        include_private = False

    recents = {}

    curs = get_db().cursor()

    args = []

    where_clauses = []
    if search:
        where_clauses.append('description LIKE ? OR extended LIKE ? OR tags LIKE ?')
        args.extend([f'%{search}%', f'%{search}%', f';{search};'])

    if include_private is False:
        where_clauses.append('shared=1')

    if username:
        where_clauses.append('owner = (select id from valued_customers where username=?)')
        args.append(username)

    if where_clauses:
        where_clause = 'WHERE ' + ' AND '.join(f'({clause})' for clause in where_clauses)
    else:
        where_clause = ''

    args.extend([limit, offset])

    curs.execute('SELECT id, created, href, description, extended, tags, big_id, shared FROM bookmarks ' \
                 + where_clause\
                 + 'ORDER BY created DESC LIMIT ? OFFSET ?', args)
    recents['columns'] = [elem[0] for elem in curs.description]
    recents['rows'] = [list(row) for row in curs.fetchall()]

    curs.close()

    return recents

def add_user(username, password_hash):
    with db_cursor() as cursor:
        cursor.execute('INSERT INTO valued_customers(username, password_hash) VALUES(?, ?)', (username, password_hash))

def _user_id_for_username(cursor, username):
    cursor.execute('SELECT id FROM valued_customers WHERE username=?', (username,))
    return cursor.fetchone()[0]

class User:
    class NotFound(Exception):
        pass

    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

        # These props required by flask-login
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    @classmethod
    def from_id(cls, user_id):
        with db_cursor() as cursor:
            cursor.execute('SELECT username FROM valued_customers WHERE id=?', (user_id,))
            if row := cursor.fetchone():
                return cls(user_id, username=row[0])
        raise cls.NotFound()

    @classmethod
    def from_api_key(cls, api_key):
        with db_cursor() as cursor:
            cursor.execute('SELECT id, username FROM valued_customers WHERE api_key=?', (api_key,))
            if row := cursor.fetchone():
                return cls(user_id=row[0], username=row[1])
        raise cls.NotFound()

    @classmethod
    def from_username_and_password(cls, username, password):
        with db_cursor() as cursor:
            cursor.execute('SELECT id, password_hash FROM valued_customers WHERE username=?', (username,))
            if row := cursor.fetchone():
                if bcrypt.checkpw(password.encode(), row[1]):
                    return cls(row[0], username)

        return None

    def get_id(self):
        return str(self.user_id)

    def get_api_key(self):
        with db_cursor() as cursor:
            cursor.execute('SELECT api_key FROM valued_customers WHERE id=?', (self.user_id,))
            return cursor.fetchone()[0]

    def set_api_key(self, api_key):
        with db_cursor() as cursor:
            cursor.execute('UPDATE valued_customers SET api_key=? WHERE id=?', (api_key, self.user_id))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('DB created. Or updated! Who knows?')

@click.command('db-import')
@click.argument('filename')
@with_appcontext
def db_import_command(filename):
    """Import bookmarks from XML dump (Delicious format or this app's extended format)."""
    db = get_db()
    cursor = db.cursor()
    user_id = None
    def start_element(name, attrs):
        nonlocal user_id

        if name == 'posts':
            user_id = _user_id_for_username(cursor, attrs['user'])
        elif name == 'post':
            new_bookmark_dict = {
                'created': datetime.datetime.strptime(attrs.get('time'), '%Y-%m-%dT%H:%M:%SZ'),
                'owner': user_id,
                'href': attrs.get('href'),
                'description': attrs.get('description'),
                'extended': attrs.get('extended'),
                'tags': Tags([tag.strip() for tag in attrs.get('tag').split(',')]),
                'big_id': attrs.get('hash'),
                'shared': attrs.get('shared', 'yes')
            }
            _new_bookmark(cursor, new_bookmark_dict, allow_big_id=True)
        else:
            # No idea
            print(f"Ignoring unknown element {name}")

    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = start_element

    if filename == '-':
        parser.ParseFile(sys.stdin.buffer)
    else:
        with open(filename, 'rb') as handle:
            parser.ParseFile(handle)

    db.commit()
    cursor.close()

@click.command('add-user')
@click.argument('username')
@with_appcontext
def db_add_user_command(username):
    password = getpass.getpass(f"Password for {username}: ")
    password = password.encode()
    password_hash = bcrypt.hashpw(password, bcrypt.gensalt())
    add_user(username, password_hash)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(db_import_command)
    app.cli.add_command(db_add_user_command)
