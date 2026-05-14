#!/usr/bin/env bash

container_name=mariadb-10
container_port=3307

docker start $container_name || docker run -d --name $container_name -p $container_port:3306 --env MARIADB_ROOT_PASSWORD=root123 mariadb:10
