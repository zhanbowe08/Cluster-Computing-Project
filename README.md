# Liveability in Melbourne: a cloud-based application 

Exploring liveability in Melbourne through social engagement and opportunity, using a cloud-based application and harvested tweets in combination with other datasets.

## Site

http://melbourneliveability.live

Note this is only accessible on the UniMelb network/VPN

## API

http://melbourneliveability.live/api/

Note this is only accessible on the UniMelb network/VPN

## Installing Dependencies

- install python dependencies from project root directory using `pip install -r modules.txt`
- install ansible dependencies from project root directory using `ansible-galaxy install -r ansible-requirements.yml`

## Database Deployment - Ansible Playbook 

- Directory `database`
- Contains ansible playbook for initialising 3 VMs and installing dependencies for couchDB.
- Cluster configuration is currently manual.
- Store the `openRC.sh` from the Melbourne Research Cloud into this directory
 
From this directory, to run the playbook, use:

```bash
./run-database.sh
```

## Twitter Harvester 

- Directory `data_harvest`
- contains Twitter data harvesters
  - `harvest.py`: uses Twitter filter streaming API
  - `searchTwitter.py`: uses Twitter 30 day search API 
- configure info in `INFO.py`

### Docker

`Dockerfile` can be used to create a docker image of the twitter harvester

## Flask 

- Directory `flask`
- Serves the ReST API
- before running the development server you need to build the frontend
- to run the development server: `flask run`
- run with gunicorn using: `gunicorn -c gunicorn.conf.py app:app`
  - access at `http://<ip address>:8000/`

### Deployment

- `flask/deployment`
- To deploy flask on the database-2 virtual machine using Ansible run `./deploy-flask.sh`
- You need to place your MRC `openRC.sh` in this directory
- During deployment, the front end is built. The relevant files for the app are zipped and 
  copied to the VM.  The VM deploys the app using nginx as the web server and gunicorn 
  as the production server for the Flask app.

### Docker

- docker image can be built from the project root as `docker build -f flask/Dockerfile sinkers/comp90024-backend .`
- push the docker image using `sinkers/comp90024-backend`
- docker compose can be run from the flask directory `docker-compose up`

## Frontend

- Directory `frontend`
- This is a `svelte` app
- in `frontend` run `npm install` to install dependencies
- to build the app run `npm run build`

## Views

- Directory `views`

### Usage

You can import couchback in your code to use following functions.
`ci = CouchInterface()
view = ci.create_regex_view([args])`
More information is shown in the test cases below `if __name__ == '__main__'` and in the docstring of each method.

### Modules

* couchback  
  It has two classes `CouchInterface` and `MapGenerator`. The first one is used to connect to a couchdb database, create views, and get the views.
  The second one can be used to quickly generate a JavaScript map function.
* preprocess  
  In this module, some functions listed to get common used views. You can create your own design documents to get custom views like the examples, but you must not use the same design name. Note that you cannot use a same design name to overwrite a design document with it.
