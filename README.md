# luserver
## A LEGO Universe server
### Created by lcdr
### License: GPL v3

### Installation
#### Dependencies
luserver requires Python 3.6 .
To run the server, you must install the dependencies, ZEO and passlib (and their dependencies). If you want to use bcrypt instead of pbkdf2_sha256 you should also install bcrypt.
Dependency installation should usually work using

	pip install passlib ZEO

or

	python -m pip install passlib ZEO

If you want the server logs to be colorful you can additionally install colorlog.

luserver also requires pyraknet, which you can download from https://bitbucket.org/lcdr/pyraknet/ . Add its installation directory to the PYTHONPATH environment variable so python can find it.
luserver should also be added to PYTHONPATH.

#### Database setup

Before the first run of the server, you'll need to initialize the database. Set the paths to the converted cdclient.sqlite and the client directory in `runtime/luserver.ini`, then run
`runtime/db/init.py`.

### Server startup

Run `runtime/__main__.py`. This sets up the auth server instance, other instances will be spawned automatically when needed.
