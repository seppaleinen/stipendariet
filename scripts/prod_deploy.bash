#!/bin/bash

set -e  # Exit on any error

# Version file to track incremental versions
VERSION_FILE=".version"

# Initialize version if file doesn't exist
if [ ! -f "$VERSION_FILE" ]; then
    echo "0" > "$VERSION_FILE"
fi

# Read current version and increment
CURRENT_VERSION=$(cat "$VERSION_FILE")
NEW_VERSION=$((CURRENT_VERSION + 1))

echo "🚀 Deploying to production (version: $NEW_VERSION)"

# Define services
SERVICES=(
    "seppaleinen/stipendariet-backend"
    "seppaleinen/stipendariet-frontend"
    "seppaleinen/stipendariet-admin"
)

# Tag and push all images
for SERVICE in "${SERVICES[@]}"; do
    echo "Tagging $SERVICE:dev -> $SERVICE:prod and $SERVICE:v$NEW_VERSION"
    
    docker tag "$SERVICE:dev" "$SERVICE:prod"
    docker tag "$SERVICE:dev" "$SERVICE:v$NEW_VERSION"
    
    echo "Pushing $SERVICE:prod..."
    docker push "$SERVICE:prod"
    
    echo "Pushing $SERVICE:v$NEW_VERSION..."
    docker push "$SERVICE:v$NEW_VERSION"
done

# Update version file
echo "$NEW_VERSION" > "$VERSION_FILE"

echo "✅ All images tagged and pushed successfully!"
echo "📦 Version: v$NEW_VERSION"

# Optional: Deploy with helmfile (uncomment if you want automatic deployment)
# echo "Deploying to production with helmfile..."
# helmfile -e production sync

echo "🎉 Production deployment complete!"