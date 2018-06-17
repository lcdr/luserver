# luserver
## A LEGO Universe server
### Created by lcdr
### Source repository at https://bitbucket.org/lcdr/luserver/
### License: [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html)

### Installation
#### Dependencies
luserver requires Python 3.6 .
Install the dependencies using

	pip install -r requirements.txt

or

	python -m pip install -r requirements.txt

If you want the server logs to be colorful you can additionally install colorlog.

luserver should be added to PYTHONPATH so python can find it.

#### Database setup

Before the first run of the server, you'll need to initialize the database. Set the paths to the converted cdclient.sqlite and the client directory in `runtime/luserver.ini`, then run
`runtime/db/init.py`.

### Server startup

Run `runtime/__main__.py`. This sets up the auth server instance, other instances will be spawned automatically when needed.

The server needs to use port 1001 for auth (hardcoded in the client). On linux this requires root permissions, to be able to start as non-root, execute `setcap 'cap_net_bind_service=+ep' /usr/bin/python3`.
