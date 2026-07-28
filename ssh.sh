#!/usr/bin/env bash
# Connect to the Board Game Logger server.
# Uses the "bgl" alias from ~/.ssh/config; falls back to the literal host if absent.
if ssh -G bgl 2>/dev/null | grep -q "^hostname 158.180.6.161$"; then
    exec ssh bgl "$@"
else
    exec ssh ubuntu@158.180.6.161 "$@"
fi
