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
    PLOT_FILE = None
    WAYPOINTS_ARRAY = []
    CUR_WAYPOINT = [0,0,0,0]
    last_pos = []

    #Static variables for updating belief grid
    TRUE_HIT = 0.97
    TRUE_MISS = 0.9

    #Static Variables to store current perception of the map
    #map[0][0] = bottom left corner
    #map[800][0] = bottom righ corner
    #map[800][800] = top right corner
    baseBelief = 0.5
    beliefMap = [[baseBelief for x in xrange(800)] for x in xrange(800)]
    mu0 = array([[0],[0],[0],[0],[0],[0]])
    sigma0 = array([[100,0,0,0,0,0],
                    [0,0.1,0,0,0,0]
                    [0,0,0.1,0,0,0]
                    [0,0,0,100,0,0]
                    [0,0,0,0,0.1,0]
                    [0,0,0,0,0,0.1]])
    H = array([[0,0,0,0,0,0]
                          [0,0,0,0,0,0]])
    H_tr = H.transpose()
    sigmaZ = array([[25,0]
                    [0,25]])
    dt = 0.5 #change in time between computations
    c = .1 #friction coeficient
    #assuming computations every 0.5 seconds
    F = array([[1,dt,(dt^2)/2,0,0,0]
                      [0,1, dt,  0,0, 0]
                      [0,-c,1,   0,0, 0]
                      [0,0, 0,   1,dt,(dt^2)/2]
                      [0,0, 0,   0,1, dt]
                      [0,0, 0,   0,-c,1]])
	F_tr = F.transpose()

    sigmaX = array([[0.1,0,0,0,0,0],
                    [0,0.1,0,0,0,0]
                    [0,0,100,0,0,0]
                    [0,0,0,0.1,0,0]
                    [0,0,0,0,0.1,0]
                    [0,0,0,0,0,100]])


    last_posx = []
    last_posy = []
    last_ang = []
    time_to_print = 0
	
	def __updateKalman(self):
		k_in = F.dot(sigmaT).dot(F_tr)+sigmaX
		k_in2 = H.dot(k_in).dot(H_tr)+sigmaZ
		k_in3 = inv(k_in2)
		k_next = k_in.dot(H_tr).dot(k_in3)
		mu_next = F.dot(mu)+k_next.dot(z_next-H.dot(F).dot(mu)
		sigmaT_next = ((identity(6)-k_next.dot(H)).dot(k_in)
		
		pos = mu_next.dot(H)
		print pos
		
		sigmaT = sigmaT_next
		mu = mu_next
		k = k_next
	
    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        if self.constants['truepositive']:
            TRUE_HIT = self.constants['truepositive']
            print 'new true hit:', TRUE_HIT
        if self.constants['truenegative']:
            TRUE_MISS = self.constants['truenegative']
            print 'new true mess:', TRUE_MISS
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
        self.last_posx = []
        self.last_posy = []
        self.last_pos = []
        self.WAYPOINTS_ARRAY = [
            [[-350,350],   [-175,350], [0,350], [175,350],  [350,350], 
                [350,250], [175,250],  [0,250], [-175,250], [-350,250]],  #Tank 1
            [[-350,150],   [-175,150], [0,150], [175,150],  [350,150], 
                [350,50],  [175,50],   [0,50],  [-175,50],  [-350,50]],   #Tank 2
            [[-350,-50],   [-175,-50], [0,-50], [175,-50],  [350,-50], 
                [350,-150],[175,-150], [0,-150],[-175,-150],[-350,-150]], #Tank 3
            [[-350,-250],  [-175,-250],[0,-250],[175,-250], [350,-250],
                [350,-350],[175,-350], [0,-350],[-175,-350],[-350,-350]]  #Tank 4
            ]
        self.last_ang = []
        for tank in mytanks:
            self.last_posx.append(tank.x-0)
            self.last_posy.append(tank.y-0)
            self.last_ang.append(tank.angle-0)
            self.last_pos.append([tank.x,tank.y])

    

    def updateBelief(self, tank):
        pos, grid = self.bzrc.get_occgrid(tank.index)

        #map coordinates are centered at 0,0; top left corner is -400, 400, top right is 400, 400, etc
        #always use given position, never the tanks position
        #position gives bottom left corner of array
        #buf = "grid x dim %d, grid y dim %d\n" % (len(grid),len(grid[0]))
        #print buf
        for relativeX in xrange(len(grid)):
            for relativeY in xrange(len(grid[0])):
                SensorX = relativeX + pos[0] + 400
                SensorY = relativeY + pos[1] + 400
                if SensorX < 0 or SensorY < 0 or SensorX >= 800 or SensorY >= 800:
                    continue
                occupied = grid[relativeX][relativeY]
                prior = self.beliefMap[SensorX][SensorY]
                if occupied == 1:
                    # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
                    Bel_Occ = self.TRUE_HIT * prior;
                    # So 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
                    Bel_Unocc = (1 - self.TRUE_MISS) * (1 - prior);
                    #now we normailze
                    self.beliefMap[SensorX][SensorY] = Bel_Occ / (Bel_Occ + Bel_Unocc);
                else:
                    # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
                    Bel_Occ = (1 - self.TRUE_HIT) * prior;
                    # So 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
                    Bel_Unocc = self.TRUE_MISS * (1 - prior);
                    #now we normailze
                    self.beliefMap[SensorX][SensorY] = Bel_Occ / (Bel_Occ + Bel_Unocc);

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
        curTanks = [mytanks[0]]
        curTanks.extend(mytanks[:4])
        if self.time_to_print < 0 :
            self.time_to_print = 20
        self.time_to_print = self.time_to_print - time_diff

        "we need a new speed, a new angle, and whether or not to shoot"
        for tank in curTanks:
            self.updateBelief(tank)
            x = tank.x
            y = tank.y
            tankWayPointIndex = self.CUR_WAYPOINT[tank.index]
            tankWayPoints = self.WAYPOINTS_ARRAY[tank.index]
            if tankWayPointIndex < len(tankWayPoints):
                speed, angle = self.get_desired_movement(tank, flags, shots, obstacles)
                shoot = self.should_shoot(tank, flags, shots, obstacles)
                if time_diff > 0:
                    velx = (tank.x-self.last_posx[tank.index])/time_diff
                    vely = (tank.y-self.last_posy[tank.index])/time_diff
                    veltheta = abs((tank.angle-self.last_ang[tank.index])/time_diff)
                else:
                    velx = 0
                    vely = 0
                    veltheta = 0
                deltaX = float(speed * math.cos(angle))
                deltaY = float(speed * math.sin(angle))
                if self.time_to_print < 0:
                    self.PLOT_FILE.write("%s %s %s %s\n" % (x, y, deltaX, deltaY))
            
                speed = speed - .001*((velx**2+vely**2)**.5)
                speed = min(speed,1)
                shoot = self.should_shoot(tank, flags, shots, obstacles)
                if angle > 0 :
                    angle = angle - .000001*veltheta
                    angle = min(angle,1)
                    command = Command(tank.index, speed, angle, shoot)
                elif angle < 0:
                    angle = angle+.000001*veltheta
                    angle = max(angle,-1)
                    command = Command(tank.index, speed, angle, shoot)
                else:
                    command = Command(tank.index, speed, 0, shoot)
                self.commands.append(command)
                
                rangeCheck = 10
                """
                print tank.x-self.last_posx[tank.index], tank.y-self.last_posy[tank.index], time_diff
                if ((tank.x-self.last_posx[tank.index]) == 0.0) and ((tank.y-self.last_posy[tank.index]) == 0.0) and time_diff > .1:
                    newPoint = [0,0]
                    tankx = int(math.floor(tank.x))
                    tanky = int(math.floor(tank.y))
                    while newPoint[0] < 10 and newPoint[1] < 10 and self.beliefMap[newPoint[0]+tankx][newPoint[1]+tanky] !=0:
                        newPoint[0] = random.randint(-50, 50)
                        newPoint[1] = random.randint(-50, 50)
                        #if self.beliefMap[]
                    newPoint[0] = newPoint[0] + tankx
                    newPoint[1] = newPoint[1] + tanky
                    print 'random', newPoint
                    tankWayPoints.insert(tankWayPointIndex, newPoint)
                """
                stuck = self.is_tank_stuck(tank)
                #print 'current goal', tankWayPoints[tankWayPointIndex], [tank.x, tank.y]
                if stuck:
                    stuck = False
                    #print 'stuck!'
                    newWayPoints = self.get_closest_reachable_gray(tank, tankWayPoints[tankWayPointIndex]);
                    #print newWayPoints
                    if newWayPoints:
                        self.WAYPOINTS_ARRAY[tank.index] = newWayPoints + self.WAYPOINTS_ARRAY[tank.index]

                if x > tankWayPoints[tankWayPointIndex][0]-rangeCheck and x < tankWayPoints[tankWayPointIndex][0]+rangeCheck:
                    if y > tankWayPoints[tankWayPointIndex][1]-rangeCheck and y < tankWayPoints[tankWayPointIndex][1]+rangeCheck:
                        self.CUR_WAYPOINT[tank.index] = tankWayPointIndex + 1
            #else we start over
            else:
                self.CUR_WAYPOINT[tank.index] = 0
            self.last_posx[tank.index] = tank.x
            self.last_posy[tank.index] = tank.y
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
        #vectors.extend(self.get_tangential_vectors(tank, obstacles))
        for speed, angle in vectors:
            final_speed += speed
            final_angle += angle
        return final_speed, final_angle

    def hasFlag(self,tank,flags):
        for flag in flags:
            if tank.flag == flag:
                return True;
        return False;



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
                update_grid(numpy.array(zip(*agent.beliefMap)))
                #update_grid(numpy.array(agent.beliefMap))
            tickCounter = tickCounter + 1
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4
