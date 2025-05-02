#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo "Deploying to Heroku with optimized requirements..."

# Push to Heroku with buildpacks and requirements file
heroku buildpacks:clear
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chrome-for-testing
heroku buildpacks:add heroku/python

# Set config variable to use production requirements
heroku config:set REQUIREMENTS_FILE=requirements-production.txt

# Check if a git remote for heroku exists
if ! git remote | grep -q heroku; then
  echo "No heroku remote found. Please set it up with:"
  echo "heroku git:remote -a YOUR_APP_NAME"
  exit 1
fi

# Push to heroku
git push heroku main

echo "Deployment complete!"