# INSTALL #

How to install:
* create database and user with followed commands
```
    sudo -u postgres psql -c "create database 'plof'";
    sudo -u postgres psql -c "create user \"plof\" with password 'plof';"
    sudo -u postgres psql -c "grant all on database \"plof\" to \"plof\";"
    sudo -u postgres psql -c "ALTER ROLE \"plof\" SUPERUSER;"
    sudo -u postgres psql -c "ALTER USER \"plof\" CREATEDB;"
```
* create virtual env for python3
```
virtualenv venv
```
* install required packages
```
./venv/bin/pip install -r requirments.txt
```
* Create tables
```
./venv/bin/python manage.py migrate
```
* Copy default local settings and set proper values
```
cp ./project/settings_local_example.py ./project/settings_local.py
vim ./project/settings_local.py

```
* Collect static files from applications and 3rd party dependencies

```
./venv/bin/python manage.py collectstatic --noinput
```

* Configure and run your webserver as usual
