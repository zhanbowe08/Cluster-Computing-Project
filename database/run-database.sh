#!/bin/bash

. ./openrc.sh; ansible-playbook database.yaml -u ubuntu --key-file=~/.ssh/database.pem
