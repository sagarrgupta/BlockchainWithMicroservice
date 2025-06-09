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