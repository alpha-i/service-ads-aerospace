#!/usr/bin/env bash
# A basic script to update a deployed version
source activate aps
git pull
pip install -r dev-requirements.txt
flask db upgrade
sudo systemctl restart api-server
sudo systemctl restart celery-worker
