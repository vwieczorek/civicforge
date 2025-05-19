#!/bin/sh
# Build the Go server
cd "$(dirname "$0")/../server" && go build -o civicforge
