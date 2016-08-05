# luserver
## A LEGO Universe server
### Created by lcdr
### License: GPL v3

### Installation
#### Dependencies
luserver requires Python 3.5 .
To run the server, you must install the dependencies, ZEO and passlib (and their dependencies). If you want to use bcrypt instead of pbkdf2_sha256 you should also install bcrypt.
Dependency installation should usually work using

	pip install <x>

or

	python -m pip install <x>

If you don't want to compile the packages yourself, you can download precompiled ones from http://www.lfd.uci.edu/~gohlke/pythonlibs/ .

##### Bugfixes

ZEO has some unfixed bugs which you'll need to fix manually:
in `<Python installation directory>/Lib/site-packages/ZEO/zrpc/client.py`
line 453
comment out:

	if socktype != socket.SOCK_STREAM:
		continue

and in `<Python installation directory>/Lib/site-packages/ZEO/zrpc/trigger.py`
line 235
change

	self.trigger.send('x')

to

	self.trigger.send(b'x')

luserver also requires pyraknet, which you can download from https://bitbucket.org/lcdr/pyraknet/ . Add its installation directory to the PYTHONPATH environment variable so python can find it.
luserver should also be added to PYTHONPATH.

#### Database setup

Before the first run of the server, you'll need to initialize the database. Set the paths to the converted cdclient.sqlite and the client's maps directory in `runtime/luserver.ini`, then run
`runtime/db/init.py`.

### Server startup

Run `runtime/__main__.py`. This sets up the auth server instance, other instances will be spawned automatically when needed.
