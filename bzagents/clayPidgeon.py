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
            speed = random.uniform(0.1, 5)
            x,y = self.get_random_point()
            self.tank_movement[tank.index] = {'speed': speed, 'x': x, 'y': y, 'last_run': time.time()}


    def get_random_point(self):
        p1 = random.uniform(-400, 400)
        p2 = 405
        isX = bool(random.getrandbits(1))
        isPos = bool(random.getrandbits(1))

        if isPos:
            p2 *= -1

        if isX:
            x = p1
            y = p2
        else:
            x = p2
            y = p1

        return x, y

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks = self.bzrc.get_mytanks()
        self.mytanks = mytanks

        self.commands = []
        #print self.tank_movement

        for tank in mytanks:
            #check if we need to bounce off the wall
            now = time.time()

            

            if self.tank_movement[tank.index]['last_run'] +5 < now and self.needs_to_bounce(tank):
                print 'we should bounce'
                self.bounce(tank)
            
            x = self.tank_movement[tank.index]['x']
            y = self.tank_movement[tank.index]['y']
            self.move_to_position(tank, x, y)

        results = self.bzrc.do_commands(self.commands)


    def needs_to_bounce(self, tank):
        if tank.x <= -395 or tank.x >= 395:
            return True
        if tank.y <= -395 or tank.y >= 395:
            return True

    ''' This will return the speed/angle needed and bounce if needed '''
    def bounce(self, tank):
        '''
        old_speed = self.tank_movement[tank.index]['speed']
        #old_angle = self.tank_movement[tank.index]['angle']

        #the speed will stay the same
        new_speed = old_speed
        new_angle = math.pi/4

        #calculate the new angle, if we need one
        if tank.x <= -395 or tank.x >= 395:
            print 'Top or Bottom bounce'
            new_angle = old_angle * -1
        if tank.y <= -395 or tank.y >= 395:
            print 'Left or Right bounce'
            if old_angle < 0:
                new_angle = math.pi/2 - old_angle
            else:
        

        self.tank_movement[tank.index]['speed'] = new_speed
        #self.tank_movement[tank.index]['angle'] = new_angle
        self.tank_movement[tank.index]['last_run'] = time.time()

        return new_speed, new_angle
        '''
        x,y = self.get_random_point()
        self.tank_movement[tank.index]['x'] = x
        self.tank_movement[tank.index]['y'] = y



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
        command = Command(tank.index, self.tank_movement[tank.index]['speed'], 2 * relative_angle, True)
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
