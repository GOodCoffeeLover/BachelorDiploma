#! /bin/bash

ELASTIC_PASSWORD=password

sudo sysctl -w vm.max_map_count=262144

docker network create elastic

docker run --name es01 --net elastic -p 9200:9200 -e "http.host=0.0.0.0" -e "transport.host=127.0.0.1" -e "xpack.security.enabled=false"  -d docker.elastic.co/elasticsearch/elasticsearch:8.2.0


docker run --name kibana --net elastic -p 5601:5601 -d docker.elastic.co/kibana/kibana:8.2.0

# docker exec -it es01 bin/elasticsearch-create-enrollment-token --scope kibana
docker exec -it kibana bin/kibana-verification-code
