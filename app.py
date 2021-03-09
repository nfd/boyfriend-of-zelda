import datetime
import os
import secrets
from xml.sax.saxutils import quoteattr

import flask
import flask_login

import db

app = flask.Flask(__name__, instance_path=os.environ['INSTANCE_PATH'])
app.config.from_mapping(
    SECRET_KEY=os.environ['SECRET_KEY'],
    DATABASE=os.path.join(app.instance_path, "db.sqlite"),
)
db.init_app(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

USER_LOGIN_DURATION = datetime.timedelta(days=365)

@login_manager.user_loader
def load_user(user_id_str):
    user_id = int(user_id_str)
    try:
        return db.User.from_id(user_id)
    except db.User.NotFound:
        return None

@login_manager.request_loader
def load_user_from_request(request):
    api_key = request.headers.get('Authorization')
    if api_key:
        api_key = api_key.split(' ', 1)[1]
        if api_key:
            try:
                return db.User.from_api_key(api_key)
            except db.User.NotFound:
                return None

@app.route('/log_in', methods=['POST'])
def log_in():
    username = flask.request.form['username']
    password = flask.request.form['password']
    if user := db.User.from_username_and_password(username, password):
        flask_login.login_user(user, remember=True, duration=USER_LOGIN_DURATION)

    return flask.redirect(flask.url_for('index_for_user', username=username))

def _index(username, is_private_user_page):
    start = flask.request.args.get('start')
    start = int(start) if start else 0

    search = flask.request.args.get('search', '').strip()
    search = search or None

    add_link_dict = {
        'url': flask.request.args.get('add'),
        'title': flask.request.args.get('title'),
        'return_to': flask.request.args.get('return_to'),
    }

    recent = db.get_bookmarks(50, offset=start, search=search, username=username,
                              include_private=is_private_user_page)
    columns = {name: idx for idx, name in enumerate(recent['columns'])}
    
    next_start = len(recent['rows']) + start
    prev_start = max(0, start - len(recent['rows'])) if start else None

    return flask.render_template('latest.html', columns=columns, rows=recent['rows'], next_start=next_start,
                                 prev_start=prev_start, search=search, is_private_user_page=is_private_user_page,
                                 add_link_dict=add_link_dict)

@app.route('/')
def index():
    return _index(None, False)

@app.route('/u/<username>')
def index_for_user(username):
    if flask_login.current_user.is_authenticated:
        is_private_user_page = username == flask_login.current_user.username
    else:
        is_private_user_page = False

    return _index(username, is_private_user_page)

@app.route('/bookmark', methods=['PUT', 'DELETE'])
@flask_login.login_required
def bookmark():
    if flask.request.method == 'DELETE':
        big_id = flask.request.json["big_id"]
        if big_id:
            db.delete_bookmark(big_id=big_id)
            return {"deleted": True}
        return {"deleted": False}
    elif flask.request.method == 'PUT':
        json_data = flask.request.json

        bookmark_dict = {
            'href': json_data['link'],
            'description': json_data['title'],
            'extended': json_data['extended'],
            'tags': db.Tags(json_data['tags'].strip().split(' ')),
            'shared': json_data['shared'],
            'big_id': json_data.get('big_id'),
            'owner': flask_login.current_user.get_id(),
        }

        if not json_data.get('big_id'):
            bookmark_dict['created'] = datetime.datetime.now()

        big_id = db.add_edit_bookmark(bookmark_dict)

        return_to = json_data.get('return_to') or '.'

        return {'updated': True, 'big_id': big_id, 'return_to': return_to}

@app.route('/apikey')
@flask_login.login_required
def show_api_key():
    api_key = flask_login.current_user.get_api_key()
    if not api_key:
        api_key = secrets.token_hex(16)
        flask_login.current_user.set_api_key(api_key)

    return flask.render_template('api_key.html', api_key=api_key)

def _db_to_xml(xml_name, columns, row):
    if xml_name in {'href', 'description', 'extended'}:
        return row[columns[xml_name]]
    elif xml_name == 'hash':
        return row[columns['big_id']]
    elif xml_name == 'tag':
        return ', '.join(row[columns['tags']])
    elif xml_name == 'time':
        return row[columns['created']].strftime('%Y-%m-%dT%H:%M:%SZ')
    elif xml_name == 'shared':
        return 'yes' if row[columns['shared']] else 'no'
    return 'huh'

@app.route('/export')
@flask_login.login_required
def export():
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<posts user="{flask_login.current_user.username}">'
    ]
    amount = 1000
    offset = 0
    while True:
        bookmarks = db.get_bookmarks(amount, offset=offset, username=flask_login.current_user.username,
                                     include_private=True)
        columns = {name: idx for idx, name in enumerate(bookmarks['columns'])}
        rows = bookmarks['rows']
        if not rows:
            break
        for row in rows:
            attrs = []
            for name in ('href', 'time', 'description', 'extended', 'tag', 'hash', 'shared'):
                value = _db_to_xml(name, columns, row)
                if not (name == 'shared' and value == 'yes'):  # Special case omit default
                    attrs.append(f'{name}={quoteattr(value)}')
            xml.append(f'<post {" ".join(attrs)} />')
        offset += amount

    xml.append('</posts>')

    return '\n'.join(xml)
