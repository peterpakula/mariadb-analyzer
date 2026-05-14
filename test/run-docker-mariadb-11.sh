#!/usr/bin/env bash

container_name=mariadb-11
container_port=3308

docker start $container_name || docker run -d --name $container_name -p $container_port:3306 --env MARIADB_ROOT_PASSWORD=root123 mariadb:11
