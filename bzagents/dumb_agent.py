#!/usr/bin/python -tt

# An incredibly simple agent.  All we do is find the closest enemy tank, drive
# towards it, and shoot.  Note that if friendly fire is allowed, you will very
# often kill your own tanks with this code.

#################################################################
# NOTE TO STUDENTS
# This is a starting point for you.  You will need to greatly
# modify this code if you want to do anything useful.  But this
# should help you to know how to interact with BZRC in order to
# get the information you need.
#
# After starting the bzrflag server, this is one way to start
# this code:
# python agent0.py [hostname] [port]
#
# Often this translates to something like the following (with the
# port name being printed out by the bzrflag server):
# python agent0.py localhost 49857
#################################################################

import sys
import math
import time
import random

from bzrc import BZRC, Command

class dumb_agent(object):
    """Class handles all command and control logic for a teams tanks."""
    new_angles = []
    running_time = []
    shooting_time = 2
    
    ENEMY_TANK_MIN_DISTANCE = 1
    ENEMY_TANK_MAX_DISTANCE = 5
    OBSTACLE_MAX_DISTANCE = 10
    OBSTACLE_MIN_DISTANCE = 1
    BULLET_MAX_DISTANCE = 10
    BULLET_MIN_DISTANCE = 1
    FLAG_MIN_DISTANCE = 1
    FLAG_MAX_DISTANCE = 5
    FLAG_MAX_SPEED = 5

    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        random.seed();
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        self.new_angles = []
        self.running_time = []
        for tank in mytanks:
            self.new_angles.append(self.normalize_angle(tank.angle - math.pi/3))
            self.running_time.append(random.uniform(3,8))
        self.shooting_time = random.uniform(1.5,2.5)
        self.commands = []

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        obstacles = self.bzrc.get_obstacles()
        self.mytanks = mytanks
        self.othertanks = othertanks
        self.flags = flags
        self.shots = shots
        self.enemies = [tank for tank in othertanks if tank.color !=
                        self.constants['team']]
        self.friendlies = [tank for tank in othertanks if tank.color ==
                        self.constants['team']]
        self.obstacles = obstacles

        self.commands = []
        shoot = False
        if self.shooting_time > 0 :
            self.shooting_time = self.shooting_time - time_diff
        else:
            shoot = True
            self.shooting_time = random.uniform(1.5,2.5)

        i = 0
        "we need a new speed, a new angle, and whether or not to shoot"
        for tank in mytanks:
            speed = 0
            angle = 0
            if self.running_time[i] > 0:
                self.running_time[i] = self.running_time[i] - time_diff
                speed = self.FLAG_MAX_SPEED
                angle = 0
            else:
                if self.new_angles[i]+.001 > tank.angle and self.new_angles[i]-.001 < tank.angle:
                    self.running_time[i] = random.uniform(3,8)
                    self.new_angles[i] = self.normalize_angle(tank.angle - math.pi/3)
                    
                else:
                    if self.new_angles[i] > 0:
                        if tank.angle - self.new_angles[i] > 1:
                            angle = -1
                        else:
                            angle = -(tank.angle-self.new_angles[i])
                    elif self.new_angles[i] < 0:
                        if self.new_angles[i] - tank.angle < -1:
                            angle = -1
                        else:
                            angle = self.new_angles[i] - tank.angle
            command = Command(tank.index, speed, angle, shoot)
            self.commands.append(command)
            i = i + 1
        results = self.bzrc.do_commands(self.commands)


    def normalize_angle(self, angle):
        """Make any angle be between +/- pi."""
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle

    def get_desired_movement(self, tank, flags, shots, obstacles):
        final_angle = 0
        final_speed = 0
        vectors = []
        vectors.extend(self.get_repulsive_vectors(tank, shots))
        vectors.extend(self.get_attractive_vectors(tank, flags))
        vectors.extend(self.get_tangential_vectors(tank, obstacles))
        for speed, angle in vectors:
            final_speed += speed
            final_angle += angle
        return final_speed, final_angle



def main():
    # Process CLI arguments.
    try:
        execname, host, port = sys.argv
    except ValueError:
        execname = sys.argv[0]
        print >>sys.stderr, '%s: incorrect number of arguments' % execname
        print >>sys.stderr, 'usage: %s hostname port' % sys.argv[0]
        sys.exit(-1)

    # Connect.
    #bzrc = BZRC(host, int(port), debug=True)
    bzrc = BZRC(host, int(port))

    agent = dumb_agent(bzrc)

    prev_time = time.time()
    # Run the agent
    try:
        while True:
            time_diff = time.time() - prev_time
            prev_time = prev_time + time_diff
            #print >> sys.stderr, 'time dif %f' % time_diff
            agent.tick(time_diff)
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4

