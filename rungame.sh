./bin/bzrflag --world=maps/no_obstacles.bzw --default-tanks=1 --default-posnoise=5 --friendly-fire --red-port=50100 --green-port=50101 --purple-port=50102 --blue-port=50103 $@ &
sleep 2
python bzagents/kalmanAgent.py localhost 50100
