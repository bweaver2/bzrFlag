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

class Agent(object):
    """Class handles all command and control logic for a teams tanks."""

    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        self.commands = []
        self.tank_movement = {}
        my_tanks = self.bzrc.get_mytanks()
        for tank in my_tanks:
            speed = random.uniform(0.5, 5)
            angle = random.uniform(math.pi/2 * -1, math.pi/2)
            self.tank_movement[tank.index] = {'speed': speed, 'angle': angle}


    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks = self.bzrc.get_mytanks()
        self.mytanks = mytanks

        self.commands = []
        print self.tank_movement

        for tank in mytanks:
            #check if we need to bounce off the wall
            speed = self.tank_movement[tank.index].speed
            angle = self.tank_movement[tank.index]..angle

            if self.needs_to_bounce(tank):
                speed, angle = self.bouce(tank)
                
            command = Command(tank.index, speed, angle, False)
            self.commands.append(command)
            
        results = self.bzrc.do_commands(self.commands)


    def needs_to_bounce(self, tank):
        if tank.x < -399 or tank.x > 399:
            return True
        if tank.y < -399 or tank.y > 399:
            return True

    ''' This will return the speed/angle needed and bounce if needed '''
    def bounce(self, tank):
        old_speed = self.tank_movement[tank.index].speed
        old_angle = self.tank_movement[tank.index].angle

        #the speed will stay the same
        new_speed = old_speed
        new_angle = old_angle

        #calculate the new angle, if we need one
        if tank.x < -399 or tank.x > 399:
            new_angle = math.pi - old_angle
        if tank.y < -399 or tank.y > 399:
            new_angle = old_angle * -1

        self.tank_movement[tank.index].speed = new_speed
        self.tank_movement[tank.index].angle = new_angle

        return new_speed, new_angle


    def attack_enemies(self, tank):
        """Find the closest enemy and chase it, shooting as you go."""
        best_enemy = None
        best_dist = 2 * float(self.constants['worldsize'])
        for enemy in self.enemies:
            if enemy.status != 'alive':
                continue
            dist = math.sqrt((enemy.x - tank.x)**2 + (enemy.y - tank.y)**2)
            if dist < best_dist:
                best_dist = dist
                best_enemy = enemy
        if best_enemy is None:
            command = Command(tank.index, 0, 0, False)
            self.commands.append(command)
        else:
            self.move_to_position(tank, best_enemy.x, best_enemy.y)

    def move_to_position(self, tank, target_x, target_y):
        """Set command to move to given coordinates."""
        target_angle = math.atan2(target_y - tank.y,
                                  target_x - tank.x)
        relative_angle = self.normalize_angle(target_angle - tank.angle)
        command = Command(tank.index, 1, 2 * relative_angle, True)
        self.commands.append(command)

    def normalize_angle(self, angle):
        """Make any angle be between +/- pi."""
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle


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

    agent = Agent(bzrc)

    prev_time = time.time()

    # Run the agent
    try:
        while True:
            time_diff = time.time() - prev_time
            agent.tick(time_diff)
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4
