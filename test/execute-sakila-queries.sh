#!/usr/bin/env bash

for container_port in 3307 3308 3309; do
    mariadb -h$HOSTNAME -P$container_port -uroot -proot123 sakila < sakila-queries.sql > /dev/null
done
