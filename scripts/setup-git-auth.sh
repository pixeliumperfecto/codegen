#!/bin/bash

# Script to configure Git to use GitHub credentials from environment variables

# Check if credentials are set in environment
if [ -z "$GITHUB_USER" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_USER or GITHUB_TOKEN not set in environment"
    echo "Add these to your ~/.bashrc file:"
    echo "export GITHUB_USER=your_username"
    echo "export GITHUB_TOKEN=your_personal_access_token"
    exit 1
fi

# Configure git to use credentials helper
git config --global credential.helper store

# Set up credentials in git config
git config --global user.name "$GITHUB_USER"
echo "https://$GITHUB_USER:$GITHUB_TOKEN@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

# Configure git to use the token for HTTPS
git config --global url."https://$GITHUB_USER:$GITHUB_TOKEN@github.com/".insteadOf "https://github.com/"

echo "Git credentials configured successfully!"
echo "Testing GitHub authentication..."

# Test authentication
if curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep -q "login"; then
    echo "✅ Authentication successful! Your credentials are working correctly."
else
    echo "❌ Authentication failed. Please check your token permissions."
fi

echo "You can now use git with GitHub without being prompted for credentials."
