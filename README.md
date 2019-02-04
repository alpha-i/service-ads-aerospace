# ADS for Aerospace

Ads for Aerospace is a paas which enable users to upload flights data and perform anomaly detection using a ML model.
The uploaded data can be used to train the model, which make the platform a living organism which can improve over time.

## Setup

```bash
$ conda create -n ads-aerospace python=3.6
$ source activate ads-aerospace
$ pip install -r dev-requirements.txt
```


## Provisioning the machine

Start the dockerized database and redis services.

```bash
$ docker-compose up -d
```

Create the configuration file `local.env` out of `local.env.dist`. Keep the same values.

Export the following evironment variable
```bash
$ export APP_CONFIG=local.env
$ export FLASK_APP=application.env
```

Run migration to create the database
```bash
$ alembic upgrade head
```

Start the web server by running
```bash
$ honcho start
```

In another shell reactivate the virtual environment, export the variables and run the provision script

```bash
$ source activate ads-aerospace

$ export APP_CONFIG=local.env
$ export FLASK_APP=application.env
$ PYTHONPATH=. python provisioning/populate.py
```

Open you browser at `http://localhost:5000` and login with the following credentials:
```
username: user@acme.com
password: userpass
```


## Test

By running

`./test.sh`

you'll get a functional test run. Currently we don't mock anything, so the unit tests need a running postgresql
and a test celery worker. This needs to change in the future (by abstracting out db access and mocking tasks).

## Documentation

[Technical Documentation](./doc/INDEX.md)

[Platform Usage](./doc/ADS-for-Aerospace-How-To.pdf)

### Platform usage Screencast

https://vimeo.com/302251572


