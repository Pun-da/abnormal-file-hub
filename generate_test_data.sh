#!/bin/bash

# Script to generate test data for monitoring dashboard
# This will upload files and make API calls to generate query logs

API_URL="http://localhost:8000/api"

echo "Generating test data for monitoring dashboard..."
echo

# Create some test files
echo "Creating test files..."
echo "Test content 1" > /tmp/test1.txt
echo "Test content 2" > /tmp/test2.txt
echo "Duplicate content" > /tmp/dup1.txt
echo "Duplicate content" > /tmp/dup2.txt
echo "Duplicate content" > /tmp/dup3.txt

# Upload files (creates query logs)
echo "Uploading files..."
curl -s -X POST -F "file=@/tmp/test1.txt" $API_URL/files/ > /dev/null
curl -s -X POST -F "file=@/tmp/test2.txt" $API_URL/files/ > /dev/null
curl -s -X POST -F "file=@/tmp/dup1.txt" $API_URL/files/ > /dev/null
curl -s -X POST -F "file=@/tmp/dup2.txt" $API_URL/files/ > /dev/null
curl -s -X POST -F "file=@/tmp/dup3.txt" $API_URL/files/ > /dev/null

# Make some GET requests (creates more query logs)
echo "Making API queries..."
for i in {1..10}; do
  curl -s $API_URL/files/ > /dev/null
  sleep 0.2
done

# Make some queries with parameters
curl -s "$API_URL/files/?search=test" > /dev/null
curl -s "$API_URL/files/?limit=5" > /dev/null

# Make a failed request (generates error log)
echo "Generating failed request..."
curl -s -X POST $API_URL/files/ > /dev/null

# Make a slow request (by calling repeatedly to simulate load)
echo "Generating query patterns..."
for i in {1..5}; do
  curl -s $API_URL/files/ > /dev/null &
done
wait

echo
echo "Test data generation complete!"
echo
echo "You should now see:"
echo "  - 5 files uploaded (3 duplicates)"
echo "  - ~20+ query logs"
echo "  - Storage savings from deduplication"
echo "  - At least 1 failed query"
echo
echo "Open http://localhost:3000 and click 'Monitoring' to view the dashboard"
echo

# Clean up temp files
rm -f /tmp/test1.txt /tmp/test2.txt /tmp/dup1.txt /tmp/dup2.txt /tmp/dup3.txt
