trap 'kill $(jobs -p)' EXIT
python3 rpcserver.py &
wait