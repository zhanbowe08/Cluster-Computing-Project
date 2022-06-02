#!/bin/bash
. ./openrc.sh; ansible-playbook deploy-flask.yaml -i hosts -u ubuntu --key-file=~/.ssh/database.pem --ask-become-pass #-vvv

