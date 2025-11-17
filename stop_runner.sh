#!/bin/bash
# Stop the TestGenEval runner server

PORT=${1:-3000}

echo "Checking for processes on port $PORT..."

PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "No process found on port $PORT"
    exit 0
fi

echo "Found process $PID on port $PORT"
ps -p $PID -o pid,command

read -p "Kill this process? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill $PID
    sleep 1
    if kill -0 $PID 2>/dev/null; then
        echo "Process still running, force killing..."
        kill -9 $PID
    fi
    echo "Process $PID stopped"
else
    echo "Cancelled"
fi

