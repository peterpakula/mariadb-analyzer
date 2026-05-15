#!/usr/bin/env bash

container_name=mariadb-10
container_port=3307
mariadb_options="--query-cache-type=ON --query-cache-size=16777216"
mariadb_options=""

docker start $container_name || docker run -d --rm --name $container_name -p $container_port:3306 --env MARIADB_ROOT_PASSWORD=root123 mariadb:10 $mariadb_options
