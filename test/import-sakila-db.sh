#!/usr/bin/env bash

for container_port in 3307 3308 3309; do
    mariadb -h$HOSTNAME -P$container_port -uroot -proot123 < sakila-db/sakila-schema.sql
    mariadb -h$HOSTNAME -P$container_port -uroot -proot123 < sakila-db/sakila-data.sql
done
