Boyfriend of Zelda
==================

Demo site: [boyfriend-of-zelda.apps.lardcave.net](https://boyfriend-of-zelda.apps.lardcave.net)

A bookmarking site. Supports the classic delicious interface of url / title / description / tags, public and private
bookmarks, adding via a bookmarklet, and multiple users.

It uses sqlite and is thus designed for a single user (or only a few users).

Setup
-----
I run this inside a Docker container -- if you would like to do that too, see the Docker section instead.
If not, you can of course run this as a Python app in the standard Pythoney way. Be sure to set `INSTANCE_PATH` to the
directory which will contain the database.

    python3 -m pip install -r requirements.txt  # Do this in a virtualenv unless this is a dedicated server
	export INSTANCE_PATH=/somewhere

Once you've configured the site (see "Configuration"), you can then start it as follows:

	gunicorn -b 127.0.0.1:80 app:app

Best practice is to put gunicorn (or the wsgi-compatible server of your choice) behind nginx, Apache, or similar.

Configuration
-------------
Before you start, you'll need to create a user:

	flask add-user yourusername

... and optionally import your Delicious / Pinboard export:

	flask db-import pinboard-or-delicious-dump.xml

Setup: Docker / Dokku / Heroku
------------------------------
The included Dockerfile means you can just `push` this to the Heroku-ish server of your choice. I use [Dokku](https://dokku.com/), so here's what I did using Dokku's command-line interface:

    dokku enter boyfriend-of-zelda /usr/local/bin/python3 -m flask add-user <username>

... set the secret key:

	dokku config:set boyfriend-of-zelda SECRET_KEY=<a large string>

... and mount permanent storage on /instance (this is optional, but if you don't do it then anything which stops the
instance, such as redeployment or a reboot, will erase your data):

	dokku storage:mount boyfriend-of-zelda /var/lib/dokku/data/storage/boyfriend-of-zelda:/instance

Usage
-----
Visit the site, click "log in", click "+", add a bookmark, repeat. Click "Edit" to edit or delete bookmarks by clicking
the icons displayed next to each entry.

Private bookmarks (click the padlock button when editing) are only shown to you and only when you're logged in.

### Bookmarklet

When you're logged in, click the face (or visit `/apikey`) to get a bookmarklet. To use the bookmarklet, copy and paste
the supplied JavaScript as the bookmark location, then click the bookmarklet when you're viewing a site you want to add.
When you add the site, you'll be redirected back to it.  You'll need to be logged in to Boyfriend of Zelda for this to
work.

XML export
----------
To export your bookmarks, log in and visit /export. This will produce a dump in Delicious XML export format. 

To do this programmatically, log in and click the face in the top right (or visit /apikey) to get your API key. You can
then pass this as an `Authorization` header. For example, here's curl:

    curl -s -H "Authorization: basic <your API key here>" https://site/export >bookmarks.xml
