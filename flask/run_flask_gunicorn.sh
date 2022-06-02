#!/usr/bin/env bash
gunicorn -D -c gunicorn.conf.py app:app
