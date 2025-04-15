#!/bin/bash
URL="https://juckkj3zo9.execute-api.eu-west-3.amazonaws.com/qa/"
while true; do
	echo "$(date +%F_%H%M%S) - $(curl -k $URL)"
	sleep 5
done