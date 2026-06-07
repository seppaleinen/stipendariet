#!/bin/bash

set -e  # Exit on any error

echo "Building Docker images in parallel..."

# Build images in parallel and capture their PIDs
docker build -t seppaleinen/stipendariet-backend:dev "$(dirname "$0")/../backend" &
PID1=$!

docker build -t seppaleinen/stipendariet-frontend:dev \
  --build-arg VITE_API_URL=/api \
  "$(dirname "$0")/../apps/frontend" &
PID2=$!

docker build -t seppaleinen/stipendariet-admin:dev "$(dirname "$0")/../apps/admin" &
PID3=$!

# Wait for all builds to complete
echo "Waiting for all builds to complete..."
FAIL=0

wait $PID1 || FAIL=1
wait $PID2 || FAIL=1
wait $PID3 || FAIL=1

# Check if any builds failed
if [ $FAIL -eq 1 ]; then
    echo "❌ One or more builds failed!"
    exit 1
fi

echo "✅ All images built successfully!"

# Deploy with helmfile
echo "Deploying with helmfile..."
helmfile -f "$(dirname "$0")/../kubernetes/helmfile.yaml" sync

echo "✅ Deployment complete!"

# Set up port-forwards for local development
echo "Setting up port-forwards..."

# Kill any existing port-forwards on these ports
pkill -f "port-forward.*service/frontend.*8080" 2>/dev/null || true
pkill -f "port-forward.*service/admin-frontend.*8081" 2>/dev/null || true
sleep 1

# Start port-forwards in background
kubectl port-forward -n stipendiatet service/frontend 8080:8080 &
kubectl port-forward -n stipendiatet service/admin-frontend 8081:80 &

echo ""
echo "✅ Port-forwards established:"
echo "   Frontend:       http://localhost:8080"
echo "   Admin Frontend: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop port-forwards"

# Wait for port-forward processes
wait