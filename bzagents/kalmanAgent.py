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
import cmath
import time
from numpy import *
from numpy.linalg import *
from operator import itemgetter, attrgetter

from bzrc import BZRC, Command

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from numpy import zeros

grid = None

def draw_grid():
    # This assumes you are using a numpy array for your grid
    width, height = grid.shape
    glRasterPos2f(-1, -1)
    glDrawPixels(width, height, GL_LUMINANCE, GL_FLOAT, grid)
    glFlush()
    glutSwapBuffers()

def update_grid(new_grid):
    global grid
    grid = new_grid



def init_window(width, height):
    global window
    global grid
    grid = zeros((width, height))
    glutInit(())
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
    glutInitWindowSize(width, height)
    glutInitWindowPosition(0, 0)
    window = glutCreateWindow("Grid filter")
    glutDisplayFunc(draw_grid)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    #glutMainLoop()

class kalmanAgent(object):
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
    PLOT_FILE = None
    WAYPOINTS_ARRAY = []
    CUR_WAYPOINT = [0,0,0,0]
    last_pos = []
    NEXT_KALMAN_UPDATE = time.time()
    LAST_ANGULAR_COMMAND = 0

    #Static variables for updating belief grid
    TRUE_HIT = 0.97
    TRUE_MISS = 0.9

    #Static Variables to store current perception of the map
    #map[0][0] = bottom left corner
    #map[800][0] = bottom righ corner
    #map[800][800] = top right corner
    baseBelief = 0.5
    beliefMap = [[baseBelief for x in xrange(800)] for x in xrange(800)]
    mu = array([[0],[0],[0],[0],[0],[0]])
    sigmaT = array([[100,0,0,0,0,0],
                    [0,0.1,0,0,0,0],
                    [0,0,0.1,0,0,0],
                    [0,0,0,100,0,0],
                    [0,0,0,0,0.1,0],
                    [0,0,0,0,0,0.1]])
    H = array([[1,0,0,0,0,0],
               [0,0,0,1,0,0]])
    H_tr = H.transpose()
    sigmaZ = array([[25,0],
                    [0,25]])
    dt = 0.5 #change in time between computations
    c = .1 #friction coeficient
    #assuming computations every 0.5 seconds
    F = array([[1,dt,(dt*dt)/2,0,0,0],
              [0,1, dt,  0,0, 0],
              [0,-c,1,   0,0, 0],
              [0,0, 0,   1,dt,(dt*dt)/2],
              [0,0, 0,   0,1, dt],
              [0,0, 0,   0,-c,1]])
    F_tr = F.transpose()

    sigmaX = array([[0.1,0,0,0,0,0],
                    [0,0.1,0,0,0,0],
                    [0,0,100,0,0,0],
                    [0,0,0,0.1,0,0],
                    [0,0,0,0,0.1,0],
                    [0,0,0,0,0,100]])


    last_posx = []
    last_posy = []
    last_ang = []
    time_to_print = 0
    
    def __updateKalman(self, z_next):
        F = self.F
        F_tr = self.F_tr
        H = self.H
        H_tr = self.H_tr
        sigmaT = self.sigmaT
        mu = self.mu
        sigmaX = self.sigmaX
        sigmaZ = self.sigmaZ

        k_in = F.dot(sigmaT).dot(F_tr)+sigmaX
        k_in2 = H.dot(k_in).dot(H_tr)+sigmaZ
        k_in3 = inv(k_in2)
        k_next = k_in.dot(H_tr).dot(k_in3)

        mu_in = z_next-H.dot(F).dot(mu) 
        mu_next = F.dot(mu) + k_next.dot(mu_in)
        sigmaT_next = ((identity(6)-k_next.dot(H)).dot(k_in))

        self.sigmaT = sigmaT_next
        self.mu = mu_next
        return H.dot(self.mu), self.sigmaT

    def get_projected_position(self, seconds):
        #make globals local for ease of use
        F = self.F
        F_tr = self.F_tr
        H = self.H
        H_tr = self.H_tr
        sigmaT = self.sigmaT
        mu = self.mu
        sigmaX = self.sigmaX
        sigmaZ = self.sigmaZ
        
        loops = int(seconds / self.dt)
        for i in xrange(loops):
            k_in = F.dot(sigmaT).dot(F_tr)+sigmaX
            k_in2 = H.dot(k_in).dot(H_tr)+sigmaZ
            k_in3 = inv(k_in2)
            k_next = k_in.dot(H_tr).dot(k_in3)

            mu_in = H.dot(F).dot(mu) 
            mu_next = F.dot(mu) + k_next.dot(mu_in)
            sigmaT_next = ((identity(6)-k_next.dot(H)).dot(k_in))

            #set up for next loop
            mu = mu_next
            k = k_next
            sigmaT = sigmaT_next

        #return where we think they will be, and our certainty of it
        return H.dot(mu), sigmaT


    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        self.commands = []
        self.PLOT_FILE = bzrc.get_plot_file()
        self.base = None
        self.time_to_print = 20
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = base
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        obstacles = self.bzrc.get_obstacles()


    def updateBelief(self, pos, noise):

        x = int(pos[0][0]) + 400
        y = int(pos[1][0]) + 400

        #print the center of the belief
        if x >= 0 and x < 800 and y >= 0 and y < 800:
            self.beliefMap[x][y] = 1

        #print the certainty ring around it at one standard deviation
        x_noise = noise[0][0]
        y_noise = noise[3][3]
        #print x,y,x_noise,y_noise
        #float[] a = new float[3*361]; // 3-coordinates and 361 angles
        for i in xrange(360):
            c_x = int(x+math.cos(i*math.pi/180)*x_noise)
            c_y = int(y+math.sin(i*math.pi/180)*y_noise)

            if c_x >= 0 and c_x < 800 and c_y >= 0 and c_y < 800:
                #print c_x,c_y
                #the ring is going to be black
                self.beliefMap[c_x][c_y] = 0

    def printAimingAt(self, target_x, target_y):
        x = int(target_x) + 400
        y = int(target_y) + 400

        #print the center of the belief
        if x >= 0 and x < 800 and y >= 0 and y < 800:
            self.beliefMap[x][y] = 1

    
    def get_observations(self):
        enemy = self.get_enemies()[0]
        return array([[enemy.x],[enemy.y]])

    def get_enemies(self):
        enemies = self.bzrc.get_othertanks()
        for tank in enemies:
            if tank.color == 'blue':
                #we only get tank positions
                return [tank]

    def clear_belief_map(self):
        self.beliefMap = [[self.baseBelief for x in xrange(800)] for x in xrange(800)]

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks = self.bzrc.get_mytanks()
        enemy = self.get_enemies()[0]
        shots = self.bzrc.get_shots()

        if enemy:
            tank = mytanks[0]
            z_next = self.get_observations()
            now = time.time()
            if(now > self.NEXT_KALMAN_UPDATE):
                self.NEXT_KALMAN_UPDATE = now + 0.5
                self.clear_belief_map();

                pos, noise = self.__updateKalman(z_next);
                self.updateBelief(pos, noise)

                #we now have some belief about the world, we should aim and soot
                self.command_turret(tank, True)
            else:
                self.command_turret(tank, True)
        else:
            command = Command(tank.index, 0, 0, False)
            self.commands.append(command)
        results = self.bzrc.do_commands(self.commands)

    #what we need to do is coordinate enemy movement with our turret
    #So we lead our target and fire when the bullet and enemy tank will cross paths
    def command_turret(self, tank, change_turn):
        #time for bullet to travel to enemy
        time = self.get_time_to_enemy(tank)
        target_x, target_y = self.get_enemy_position(time)
        self.printAimingAt(target_x, target_y)
        """Set command to move to given coordinates."""
        target_angle = math.atan2(target_y - tank.y,
                                  target_x - tank.x)
        relative_angle = self.normalize_angle(target_angle - tank.angle)
        should_shoot = False
        #if are hit within 2.5 degrees then shoot
        if abs(relative_angle) < math.pi/144:
            should_shoot = True
        if change_turn:
            self.LAST_ANGULAR_COMMAND = 4 * relative_angle

        command = Command(tank.index, 0, self.LAST_ANGULAR_COMMAND, should_shoot)
        self.commands.append(command)

    def get_time_to_enemy(self, tank):
        e_x_p = self.mu[0][0]
        e_x_v = self.mu[1][0]
        e_x_a = self.mu[2][0]
        e_y_p = self.mu[3][0]
        e_y_v = self.mu[4][0]
        e_y_a = self.mu[5][0]
        e_v = math.sqrt(e_x_v ** 2 + e_y_v ** 2)
        e_a = math.sqrt(e_x_a ** 2 + e_y_a ** 2)

        b_x_p = tank.x
        b_y_p = tank.y
        #from constants.py: SHOTSPEED = 100
        b_y_v = 100
        b_y_a = 0

        dist = math.sqrt((b_x_p - e_x_p)**2 + (b_y_p - e_y_p)**2)

        #image a circle radiating outwards with time. 
        #This represents the shot fired (traveling at a rate of 100)
        #bullet_position = tank_position + bullet_velocity*t
        #enemy_position = enemy_position + enemy_velocity * t + enemy_accl*t^2/2
        #tank_position + bullet_velocity * t - enemy_position - enemy_velocity * t - (enemy_accl * t^2)/2 = 0
        #e_p + e_v * t + (1/2) e_a * t^2 = b_p + b_v * t
        #t(100 - e_v) + 1/2 e_a * t^2 = b_p - e_p (which is dist)
        a = 1/2 * e_a
        b = 100 - e_v
        c = dist * -1
        if a != 0:
            root_check = b**2 - 4*a*c
            if root_check > 0:
                root1 = (-b - math.sqrt(root_check)) / (2*a)
                root2 = (-b + math.sqrt(root_check)) / (2*a)
                if root1 > root2:
                    return root1
                else:
                    return root2
            else:
                return None
        else:
            return dist/(100 - e_v)

    def get_enemy_position(self, time):
        e_x_p = self.mu[0][0]
        e_x_v = self.mu[1][0]
        e_x_a = self.mu[2][0]
        e_y_p = self.mu[3][0]
        e_y_v = self.mu[4][0]
        e_y_a = self.mu[5][0]

        new_x = e_x_p + time*e_x_v + (1/2)*e_x_a*time**2
        new_y = e_y_p + time*e_y_v + (1/2)*e_y_a*time**2
        return new_x, new_y

    def normalize_angle(self, angle):
        """Make any angle be between +/- pi."""
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle



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

    agent = kalmanAgent(bzrc)

    init_window(800,800)
    # Run the agent
    try:
        tickCounter = 0
        prev_time = time.time()
        while True:
            time_diff = time.time() - prev_time
            prev_time = time.time()
            agent.tick(time_diff)
            if tickCounter % 10 == 0:
                draw_grid()
                update_grid(array(zip(*agent.beliefMap)))
                #update_grid(numpy.array(agent.beliefMap))
            tickCounter = tickCounter + 1
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4
