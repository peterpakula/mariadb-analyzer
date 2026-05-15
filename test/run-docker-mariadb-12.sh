#!/usr/bin/env bash

container_name=mariadb-12
container_port=3309
mariadb_options=""

docker start $container_name || docker run -d --rm --name $container_name -p $container_port:3306 --env MARIADB_ROOT_PASSWORD=root123 mariadb:12 $mariadb_options
