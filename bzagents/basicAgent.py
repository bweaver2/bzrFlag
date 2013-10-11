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
from numpy import *

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
        self.base = None
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = base

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
        curTanks = []
        curTanks.extend(mytanks)
        #curTanks.append(mytanks[0])

        "we need a new speed, a new angle, and whether or not to shoot"
        for tank in curTanks:
            speed, angle = self.get_desired_movement(tank, flags, shots, obstacles)
            shoot = self.should_shoot(tank, flags, shots, obstacles)
            if angle > 0 :
                command = Command(tank.index, speed, 1, shoot)
            elif angle < 0:
                command = Command(tank.index, speed, -1, shoot)
            else:
                command = Command(tank.index, speed, 0, shoot)
            self.commands.append(command)

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
        #vectors.extend(self.get_repulsive_vectors(tank, shots))
        vectors.extend(self.get_attractive_vectors(tank, flags))
        vectors.extend(self.get_tangential_vectors(tank, obstacles))
        for speed, angle in vectors:
            final_speed += speed
            final_angle += angle
        return final_speed, final_angle

    def get_repulsive_vectors(self, tank, shots):
        speeds = []
        angles = []
        """for enemy in self.enemies:
            if enemy.status != 'alive':
                continue
            dist = math.sqrt((enemy.x - tank.x)**2 + (enemy.y - tank.y)**2)
            if self.ENEMY_TANK_MIN_DISTANCE < dist < self.ENEMY_TANK_MAX_DISTANCE:
                target_angle = math.atan2(enemy.y - tank.y, enemy.x - tank.x)
                relative_angle = self.normalize_angle(target_angle - tank.angle)
                repel_angle = self.normalize_angle(relative_angle + 180)
                tangent_angle = self.normalize_angle(relative_angle + 90)
                speeds.append(1/dist)
                angles.append(repel_angle)
                speeds.append(1/dist)
                angles.append(tangent_angle)"""
        #for shot in shots
            #do stuff like check if the bullet is heading towards us, to dodge it
        return zip(speeds, angles)

    def hasFlag(self,tank,flags):
        for flag in flags:
            if tank.flag == flag:
                return True;
        return False;

    def get_attractive_vectors(self, tank, flags):
        speeds = []
        angles = []
        speed = 0
        angle = 0
        bestFlag = None
        bestDist = None
        for flag in flags:
            
            if (tank.flag == "-" and flag.color != self.constants['team']):
                dist = math.sqrt((flag.x - tank.x)**2 + (flag.y - tank.y)**2)
                if bestDist == None or dist < bestDist:
                    bestFlag = flag
                    bestDist = dist
                    target_angle = math.atan2(flag.y - tank.y, flag.x - tank.x)
                    relative_angle = self.normalize_angle(target_angle - tank.angle)
                    if dist > self.FLAG_MAX_DISTANCE:
                        speed = self.FLAG_MAX_SPEED
                        angle = relative_angle
                    elif dist > self.FLAG_MIN_DISTANCE:
                        speed = dist
                        angle = relative_angle
            elif (tank.flag != "-" and flag.color != self.constants['team']):
                #run home depo
                target_angle1 = math.atan2(self.base.corner1_y - tank.y, self.base.corner1_x - tank.x)
                target_angle2 = math.atan2(self.base.corner2_y - tank.y, self.base.corner2_x - tank.x)
                target_angle3 = math.atan2(self.base.corner3_y - tank.y, self.base.corner3_x - tank.x)
                target_angle4 = math.atan2(self.base.corner4_y - tank.y, self.base.corner4_x - tank.x)
                
                relative_angle1 = self.normalize_angle(target_angle1 - tank.angle)
                relative_angle2 = self.normalize_angle(target_angle2 - tank.angle)
                relative_angle3 = self.normalize_angle(target_angle3 - tank.angle)
                relative_angle4 = self.normalize_angle(target_angle4 - tank.angle)
                
                speeds.extend([5,5,5,5])
                angles.extend([relative_angle1,relative_angle2,relative_angle3,relative_angle4])
                    
        speeds.append(speed)
        angles.append(angle)
        return zip(speeds, angles)

    def get_tangential_vectors(self, tank, obstacles):
        speeds = []
        angles = []
        
        #obstacles like walls are interesting, we can't define them as points so we need to be a little more specific
        #each obstacle is a set of 4 points defining a rectangle
        for obstacle in obstacles:
            intersection = self.will_hit_obstacle(tank, obstacle)
            if intersection != None:
                #we are only applying tangential forces
                dist = math.sqrt((intersection[0] - tank.x)**2 + (intersection[1] - tank.y)**2)
                if self.OBSTACLE_MIN_DISTANCE < dist < self.OBSTACLE_MAX_DISTANCE:
                    target_angle = math.atan2(intersection[1] - tank.y, intersection[0] - tank.x)
                    tangent_angle = self.normalize_angle(target_angle + 90)
                    relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                    speeds.append(1/dist)
                    angles.append(tangent_angle)
        return zip(speeds, angles)
    
    #returns a pair of points defining a line
    def will_hit_obstacle(self, tank, obstacle):
        #first we need to make the lines to check for collissions.
        
        lines =[(array( [obstacle[0][0], obstacle[0][1] ] ), array( [obstacle[1][0], obstacle[1][1] ] )), 
                (array( [obstacle[1][0], obstacle[1][1] ] ), array( [obstacle[2][0], obstacle[2][1] ] )), 
                (array( [obstacle[2][0], obstacle[2][1] ] ), array( [obstacle[3][0], obstacle[3][1] ] )), 
                (array( [obstacle[3][0], obstacle[3][1] ] ), array( [obstacle[0][0], obstacle[0][1] ] ))]
        
        #calculate a future point along the tank's trajectory
        newTankX = float(self.OBSTACLE_MAX_DISTANCE * math.cos(tank.angle))
        newTankY = float(self.OBSTACLE_MAX_DISTANCE * math.sin(tank.angle))
        tankLine = [array( [tank.x, tank.y] ), array( [newTankX, newTankY] )]
        
        collisions = []
        for line in lines:
            if intersect(line[0], line[1], tankLine[0], tankLine[1]):
                collisions.append(line)
        
        closestIntersection = None
        closestDist = None
        for p1, p2 in collisions:
            intersection = seg_intersect(p1, p2, tankLine[0], tankLine[1])
            dist = math.sqrt((intersection[0] - tank.x)**2 + (intersection[0] - tank.y)**2)
            if closestDist == None or dist < closestDist:
                closestDist = dist
                closestIntersection = intersection
        
        return closestIntersection
                    

    def should_shoot(self, tank, flags, shots, obstacles):
        return True

#borrowed from http://www.cs.mun.ca/~rod/2500/notes/numpy-arrays/numpy-arrays.html
#
# line segment intersection using vectors
# see Computer Graphics by F.S. Hill
#
def perp( a ) :
    b = empty_like(a)
    b[0] = -a[1]
    b[1] = a[0]
    return b

# line segment a given by endpoints a1, a2
# line segment b given by endpoints b1, b2
# return 
def seg_intersect(a1,a2, b1,b2) :
    da = a2-a1
    db = b2-b1
    dp = a1-b1
    dap = perp(da)
    denom = dot( dap, db)
    num = dot( dap, dp )
    return (num / denom)*db + b1    
    
    
#borrowed from http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def ccw(A,B,C):
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def intersect(A,B,C,D):
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

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
