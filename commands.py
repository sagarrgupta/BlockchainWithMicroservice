# To get the chain
curl http://localhost:5002/chain
curl http://localhost:5003/chain
curl http://localhost:5004/chain

# To get the nodes
curl http://localhost:5002/nodes
curl http://localhost:5003/nodes
curl http://localhost:5004/nodes

# To add a user
curl -X POST http://localhost:5002/add_user \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "name": "Sagar",
           "initial_balance": 100
         }'

# To add a user
curl -X POST http://localhost:5002/add_user \
     -H "Content-Type: application/json" \
     -d '{
           "id": 2,
           "name": "Mohit",
           "initial_balance": 200
         }'

# To transfer
curl -X POST http://localhost:5002/transfer \
     -H "Content-Type: application/json" \
     -d '{"from_id": 42, "to_id": 1, "amount": 2}'

# To get the balance
curl http://localhost:5004/request/1
curl http://localhost:5004/request/2

# To remove docker image
docker stop $(docker ps -q --filter "name=blockchainwithmicroservices") 2>/dev/null
docker rm   $(docker ps -a -q --filter "name=blockchainwithmicroservices") 2>/dev/null

# To start docker
docker-compose build --no-cache              
docker-compose up -d

# To check the logs
docker compose logs -f provider_service

# To get into shell
docker exec -it blockchainwithmicroservice-requester_service-1 sh

# To send multiple requests
curl http://provider_service:5003/user/1
curl http://provider_service:5003/user/2
curl http://provider_service:5003/user/3

# To run more services
docker compose up --scale provider_service=3;

# To get resource
curl http://127.0.0.1:5003/request/1

# To update resource
curl -X POST http://localhost:5003/update_resource/1/high

# time it takes
# normal: 7.63 ms
# with blockchain with 1 block: 15.02 ms (96.8%)
# with blockchain with 2 blocks: 21.34 ms (179.6%, 42.1%)

# node1 = 2 chain - 5002
# node2 = 2 chain
# node3 = 1 chain -> register -> it passes longest chain -> copy local -> 2 chain

# shouldExternalUserCanChange = true/false
# /customChangeToDatabase 

"""

"""