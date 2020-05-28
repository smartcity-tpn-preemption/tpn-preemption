#!/usr/bin/env python

import os
import sys

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
  tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
  sys.path.append(tools)
else:
  sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

import logging
import optparse
from distutils.util import strtobool

from classes.logger import Logger
from classes.statistics_values import StatisticsValues
from classes.configuration import Configuration
from classes.no_preemption import NoPreemptionStrategy
from classes.smartcity_centered import SmartcityCenteredStrategy
from classes.rfid_preemption import RfidPreemptionStrategy
from classes.djahel import DjahelStrategy
from classes.smartcity_petri import SmartcityPetriStrategy


logger = None

def get_options():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option("--nogui", action="store_true",
                        default=False, help="run the commandline version of sumo")
  opt_parser.add_option("--scenario", dest="scenario_folder", 
                        help="Scenario folder which the simulation will use", metavar="FILE")
  opt_parser.add_option("--sync", type="string", dest="sync",
                        default="False", help="Indicates if traffic lights should resync after preemption")
  opt_parser.add_option('--sf', '--speedfactor', type="float", dest="speedfactor", default=2.0)
  opt_parser.add_option('--df', '--distancefactor', type="float", dest="distancefactor", default=2.0)
  opt_parser.add_option('--tf', '--thresholdfactor', type="float", dest="thresholdfactor", default=2.0)
  opt_parser.add_option('--sm', '--seed-sumo', type="int", dest="seedsumo", default=0)
  opt_parser.add_option("--ev", type="string", dest="ev", default="veh1")  
  opt_parser.add_option('--alg', type="string", dest="algorithm", default="no-preemption")
  opt_parser.add_option('--distancedetection', type="float", dest="distancedetection", default=50.0)
  opt_parser.add_option('--ncycles', type="int", dest="ncycles", default=2)
  opt_parser.add_option('--override', action="store_true",
                        default=False, help="run only if .json doesn't exist") 
  opt_parser.add_option('--skip', action="store_true",
                        default=False, help="json file is not generated in the end")
  opt_parser.add_option("--prefix", type="string", dest="prefix",
                        default="staticdynamic", help="Choose between static/dynamic scenarios")
  opt_parser.add_option("--el", type="string", dest="el",
                        default="low", help="Emergency Level for Djahel (low, medium, high)")
  opt_parser.add_option("--when-check", type="string", dest="whencheck",
                        default="start", help="Djahel must know when generate ERP commands (start,lane)")
  opt_parser.add_option("--lc", type="string",  dest="localcancelling",
                        default='False', help="Local or Global Cancelling method")                                                         
  (options, args) = opt_parser.parse_args()
  return options

def run(options, algorithm, statistics_values):
  #we need a fixed seed to keep the experiments reproducible
  #we choose the total number of passenger vehicles (osm.passenger.trips.xml file)
  logger.info('algorithm: ' + str(options.algorithm))

  ev = statistics_values.ev

  logger.info('Chosen EV '+str(ev))

  ev_entered_in_simulation = False   
  conf = Configuration(ev,options.scenario_folder)

  if options.prefix == 'staticdynamic':
    conf.set_staticdynamic()

  logger.info('tls order')
  logger.info([conf.edges[edge]['tl']['name'] for edge in conf.edges_order if edge in conf.edges_with_tl ])

  algorithm.setup(conf,statistics_values,ev)

  algorithm.configure()

  # return
  while traci.simulation.getMinExpectedNumber() > 0:
    step = int(traci.simulation.getTime())
    statistics_values.update_cars_by_time(step,traci.vehicle.getIDCount())

    algorithm.execute_before_step_simulation(step)              

    logger.info('step '+str(step))
    traci.simulationStep()
    

    if not ev_entered_in_simulation:
      ev_entered_in_simulation, when_entered = track_vehicle(ev, options, step)

    if ev_entered_in_simulation and statistics_values.n_when_ev_enter < 0:
        algorithm.conf.update_values()
        statistics_values.n_when_ev_enter = traci.vehicle.getIDCount() - 1
        statistics_values.update_vehicles_affected_by_ev_dispatch()

    algorithm.execute_step(step,ev_entered_in_simulation)

    if ev in traci.vehicle.getIDList():
      statistics_values.update_vehicles_affected_by_ev()      
      statistics_values.distance_travelled = traci.vehicle.getDistance(ev)
      statistics_values.update_vehicles_on_tl()
      logger.info('ev '+str(ev)+' has travelled '+str(statistics_values.distance_travelled)+'m')

    if ev in traci.simulation.getStartingTeleportIDList():
      statistics_values.was_teleported = True  

    if statistics_values.ev_end == -1 and (traci.vehicle.getIDCount() <= 0 or (ev_entered_in_simulation and ev not in traci.vehicle.getIDList())):
      if ev_entered_in_simulation and ev not in traci.vehicle.getIDList():
        statistics_values.ev_end = step
        statistics_values.n_when_ev_left = traci.vehicle.getIDCount() - 1
        statistics_values.ev_start = when_entered
        algorithm.finish()

      if statistics_values.was_teleported:
        logger.info(str(ev)+' has been teleported!')

    statistics_values.n_of_teleporteds |= set(traci.simulation.getStartingTeleportIDList())

  statistics_values.crossed_tls_by_ev = len(algorithm.conf._edges_with_tl)

  statistics_values.print_summary(ev)

  traci.close()
  sys.stdout.flush()

  logger.info('finished!')
  logger.info('ev('+str(ev)+') started '+str(statistics_values.ev_start)+' and ended '+str(statistics_values.ev_end))

  statistics_values.get_results(ev,step)

  statistics_values.generate_json(options.skip,algorithm.instance_name())

def track_vehicle(ev, options, step):
  if ev in traci.vehicle.getIDList():
    if not options.nogui:
      traci.gui.trackVehicle('View #0',ev)
      traci.gui.setZoom('View #0',10000)
      traci.vehicle.setColor(ev, (255,0,0))

    logger.info('ev entered in network in '+str(step))
    return True,step

  return False,0

# this is the main entry point of this script
if __name__ == "__main__":
  options = get_options()

  try:
    strtobool(options.sync)
    print(options)
  except:
    sys.exit("Error: --sync option invalid. It should be true or false")

  if not options.scenario_folder:
    sys.exit("Error: You must specify the Scenario Folder using the '--scenario' option")

  if options.prefix != 'static' and options.prefix != 'dynamic' and options.prefix != 'staticdynamic':
    sys.exit("Error: --prefix should be 'static', 'dynamic' or 'staticdynamic'")

  if options.el != 'low' and options.el != 'medium' and options.el != 'high':
    sys.exit("Error: Emergency Level must be one of those options: low, medium or high")

    if options.whencheck != 'start' and options.whencheck != 'lane':
      sys.exit("Error: when-check must be start or lane")    

  if options.nogui:
      sumoBinary = checkBinary('sumo')
  else:
      sumoBinary = checkBinary('sumo-gui')

  if options.algorithm == 'smartcity-centered':
    algorithm = SmartcityCenteredStrategy(options)
  elif options.algorithm == 'rfid':
    algorithm = RfidPreemptionStrategy(options)
  elif options.algorithm == 'no-preemption':
    algorithm = NoPreemptionStrategy(options)
  elif options.algorithm == 'djahel':
    algorithm = DjahelStrategy(options)
  elif options.algorithm == 'petri':
    algorithm = SmartcityPetriStrategy(options)
  else:
    sys.exit("Error: --alg was not recognized: "+options.algorithm)

  instance_folder = os.path.join(options.scenario_folder,'results')
  instance_folder = os.path.join(instance_folder,options.prefix)

  if not os.path.exists(instance_folder):
    os.makedirs(instance_folder, exist_ok=True)

  instance_opts = 'tripinfo_'+ algorithm.instance_name()

  logfile = os.path.join(instance_folder, '{}.log'.format(instance_opts)) 

  Logger.set_globals(logfile,logging.INFO)

  logger = Logger('Runner').get()

  logger.info(options)

  trip_file = instance_folder+'/'+instance_opts+'.xml'

  statistics_values = StatisticsValues(options.scenario_folder, instance_folder, trip_file, options.algorithm, options.ev)

  if not statistics_values.skip_because_json_file(options.override, options.skip, algorithm.instance_name()):
    traci.start([sumoBinary, '-v','true','-c', options.scenario_folder+'/osm-'+options.prefix+'.sumocfg','--duration-log.statistics',
                            '--tripinfo-output', trip_file, '--start', '--time-to-teleport', '300', '--seed', str(options.seedsumo), 
                            '--ignore-junction-blocker', '50'])

    logger.info('SUMO Version: {}'.format(traci.getVersion()))                            

    run(options, algorithm, statistics_values)

    if os.path.isfile(trip_file):
      os.remove(trip_file)
      logger.info('File {} was deleted'.format(trip_file))

    if os.path.isfile(logfile):
      logger.info('Deleting {}...'.format(logfile))
      os.remove(logfile)
