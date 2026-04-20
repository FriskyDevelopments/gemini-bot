#!/bin/bash
# Script to manually hibernate the cloud instance during local dev
# Usage: ./stop_cloud.sh [RESOURCE_GROUP]

RG_NAME=${1:-"gemini-bot-rg"}
APP_NAME="gemini-bot"

echo "🛑 Attempting to stop Azure Container App: $APP_NAME in Resource Group: $RG_NAME..."

if command -v az &> /dev/null
then
    az containerapp stop --name "$APP_NAME" --resource-group "$RG_NAME"
    if [ $? -eq 0 ]; then
        echo "✅ Successfully sent stop command to Azure."
    else
        echo "❌ Failed to stop the container app. Check your Azure CLI login and permissions."
    fi
else
    echo "⚠️ Azure CLI (az) is not installed. Please install it to use this script."
fi
