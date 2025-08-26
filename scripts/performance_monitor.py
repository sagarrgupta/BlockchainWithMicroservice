# Tab 1 - Continuous Requests:
while true; do
  echo "$(date '+%H:%M:%S.%3N') Request:"
  curl -w "Response Time: %{time_total}s\n" -s http://localhost:5003/request/1 | grep -E "(message|Response Time)"
  sleep 0.5
done

while true; do
  echo "$(date '+%H:%M:%S.%3N') Request:"
  curl -w "Response Time: %{time_total}s\n" -s -X POST http://localhost:5003/update_resource/1/medium | grep -E "(message|Response Time)"
  sleep 0.05
done

# Tab 2 - Monitor Pods:
kubectl get pods -n blockchain-microservices -w

# Tab 3 - Monitor HPA:
kubectl get hpa -n blockchain-microservices -w

# Tab 4 - Monitor Scaling Events:
kubectl get events -n blockchain-microservices --watch | grep -E "(HPA|Scale|Scaled)"

# Tab 5 - Performance Test with Mining:
chmod +x performanceTestWithMining.sh
./performanceTestWithMining.sh

# Tab 6 - Performance Test without Mining:
chmod +x performanceTestWithoutMining.sh
./performanceTestWithoutMining.sh
