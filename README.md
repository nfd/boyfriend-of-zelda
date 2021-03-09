Boyfriend of Zelda
==================

A bookmarking site. Documentation TODO, but if you're keen, it's a Flask Python app -- the basics are (fish shell
syntax):

	python3 -m venv /path/to/venv
	source /path/venv/bin/activate.fish
	pip install -r requirements.txt

	export FLASK_APP=app
	mkdir instance
	export INSTANCE_PATH=(pwd)/instance
	flask init-db
	flask add-user yourusername
	flask db-import pinboard-or-delicious-dump.xml  # optional
	flask run
