./bin/bzrflag --world=maps/small_four_ls.bzw --friendly-fire --default-tanks=1 --red-port=50100 --green-port=50101 --purple-port=50102 --blue-port=50103 --default-true-positive=0.97 --default-true-negative=0.9 --occgrid-width=100 $@ &
sleep 2
python bzagents/basicAgent.py localhost 50100 
