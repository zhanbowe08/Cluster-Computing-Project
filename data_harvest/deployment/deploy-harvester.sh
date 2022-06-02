#!/bin/bash
. ./openrc.sh; ansible-playbook deploy-harvester.yaml -u ubuntu --key-file=~/.ssh/database.pem --ask-become-pass -vvv
