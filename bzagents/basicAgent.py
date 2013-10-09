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

from bzrc import BZRC, Command

class basicAgent(object):
    """Class handles all command and control logic for a teams tanks."""
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
        self.commands = []

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks, othertanks, flags, shots, obstacles = self.bzrc.get_lots_o_stuff()
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

        "we need a new speed, a new angle, and whether or not to shoot"
        for tank in mytanks:
            speed, angle = self.get_desired_movement(tank, flags, shots, obstacles)
            shoot = self.should_shoot(tank, flags, shots, obstacles)
            command = Command(tank.index, speed, angle, shoot)
            self.commands.append(command)

        results = self.bzrc.do_commands(self.commands)

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
        return speed, angle

    def get_repulsive_vectors(self, tank, shots):
        speeds = []
        angles = []
        for enemy in self.enemies:
            if enemy.status != 'alive':
                continue
            dist = math.sqrt((enemy.x - tank.x)**2 + (enemy.y - tank.y)**2)
            if self.ENEMY_TANK_MIN_DISTANCE < dist < self.ENEMY_TANK_MAX_DISTANCE:
                target_angle = math.atan2(enemy.y - tank.y, enemy.x - tank.x)
                relative_angle = self.normalize_angle(target_angle - tank.angle)
                repel_angle = self.normalize_angle(target_angle + 180)
                tangent_angle = self.normalize_angle(target_angle + 90)
                speeds.append(1/dist)
                angles.append(repel_angle)
                speeds.append(1/dist)
                angles.append(tangent_angle)
        #for shot in shots
            #do stuff like check if the bullet is heading towards us, to dodge it
        return zip(speeds, angles)



    def get_attractive_vectors(self, tank, flags):
        speeds = []
        angles = []
        for flag in flags:
            if flag.color != self.constants['team']:
                dist = math.sqrt((flag.x - tank.x)**2 + (flag.y - tank.y)**2)
                target_angle = math.atan2(flag.y - tank.y, flag.x - tank.x)
                if dist > self.FLAG_MAX_DISTANCE:
                    speeds.append(self.FLAG_MAX_SPEED)
                    angles.append(target_angle)
                elif dist > self.FLAG_MIN_DISTANCE:
                    speeds.append(dist)
                    angles.append(target_angle)
        return zip(speeds, angles)

    def get_tangential_vectors(self, tank, obstacles):
        speeds = []
        angles = []
        for obstacle in obstacles:
            dist = math.sqrt((obstacle[0][0] - tank.x)**2 + (obstacle[0][1] - tank.y)**2)
            if self.OBSTACLE_MIN_DISTANCE < dist < self.OBSTACLE_MAX_DISTANCE:
                target_angle = math.atan2(obstacle[0][1] - tank.y, obstacle[0][0] - tank.x)
                relative_angle = self.normalize_angle(target_angle - tank.angle)
                tangent_angle = self.normalize_angle(target_angle + 90)
                speeds.append(1/dist)
                angles.append(tangent_angle)
        return zip(speeds, angles)


    def should_shoot(self, tank, flags, shots, obstacles):
        return True


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

    agent = basicAgent(bzrc)

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
