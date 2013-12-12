./bin/bzrflag --world=maps/no_obstacles.bzw --red-tanks=1 --blue-tanks=1 --green-tanks=0 --purple-tanks=0 --default-posnoise=5 --friendly-fire --red-port=50100 --green-port=50101 --purple-port=50102 --blue-port=50105 $@ &
sleep 2 
python bzagents/kalmanAgent.py localhost 50100 &
python bzagents/clayPidgeon.py localhost 50105
