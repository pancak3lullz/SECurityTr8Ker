#!/bin/bash
# SECurityTr8Ker Message Sender Wrapper
# 
# This script is a convenience wrapper for sending messages to the 
# SECurityTr8Ker Docker container.
#
# Usage:
#   ./sectracker-send.sh [options] "Your message here"
#
# Options:
#   --channels=slack,teams    Comma-separated list of channels
#   --prefix="[Custom]"       Custom prefix for the message
#   --debug                   Enable debug mode
#   --container=name          Docker container name (default: securitytracker)
#   --help                    Show this help message

# Default values
CONTAINER="securitytracker"
DEBUG=""
CHANNELS=""
PREFIX=""
MESSAGE=""
SHOW_HELP=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --container=*)
      CONTAINER="${arg#*=}"
      shift
      ;;
    --channels=*)
      CHANNELS="--channels ${arg#*=}"
      shift
      ;;
    --prefix=*)
      PREFIX="--prefix ${arg#*=}"
      shift
      ;;
    --debug)
      DEBUG="--debug"
      shift
      ;;
    --help)
      SHOW_HELP=true
      shift
      ;;
    *)
      if [ -z "$MESSAGE" ]; then
        MESSAGE="$arg"
      fi
      shift
      ;;
  esac
done

# Show help if requested or if no message provided
if $SHOW_HELP || [ -z "$MESSAGE" ]; then
  echo "SECurityTr8Ker Message Sender"
  echo ""
  echo "Usage:"
  echo "  ./sectracker-send.sh [options] \"Your message here\""
  echo ""
  echo "Options:"
  echo "  --channels=slack,teams    Comma-separated list of channels"
  echo "  --prefix=\"[Custom]\"       Custom prefix for the message"
  echo "  --debug                   Enable debug mode"
  echo "  --container=name          Docker container name (default: securitytracker)"
  echo "  --help                    Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./sectracker-send.sh \"System maintenance scheduled for tomorrow\""
  echo "  ./sectracker-send.sh --channels=slack,teams \"Important update\""
  echo "  ./sectracker-send.sh --prefix=\"[URGENT]\" \"Critical information\""
  
  # Exit with error if no message provided and not explicitly asking for help
  if [ -z "$MESSAGE" ] && ! $SHOW_HELP; then
    exit 1
  else
    exit 0
  fi
fi

# Build the command
CMD="sectracker-message $CHANNELS $PREFIX $DEBUG \"$MESSAGE\""

# Execute the command in the container
echo "Sending message to $CONTAINER container..."
docker exec -it $CONTAINER bash -c "$CMD"

# Check exit status
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "Message sent successfully!"
else
  echo "Failed to send message. Exit code: $STATUS"
  exit $STATUS
fi 