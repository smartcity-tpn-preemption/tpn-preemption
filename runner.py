#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random
import xml.etree.ElementTree
import math
import logging


# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

from classes.default_worker import DefaultWorker
from classes.preemption_worker import PreemptionWorker
from classes.statistics_values import StatisticsValues
from classes.threaded_http_server import WebhookServer
from classes.logger import Logger

logger = None


def run(withpreemption, folder, trip_file):
    #we need a fixed seed to keep the experiments reproducible
    #we choose the total number of passenger vehicles (osm.passenger.trips.xml file)
    statisticsValues = StatisticsValues(folder, trip_file)

    statisticsValues.prepareExperiment()

    if(withpreemption):
      worker = PreemptionWorker(statisticsValues.evList, 100.00, folder)
    else:
      worker = DefaultWorker(statisticsValues.evList, 100.00, folder)
    if(not worker.preConfig()):
      logger.error('Some EVs could not be registered, aborting...')
      return

    """execute the TraCI control loop"""
    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        logger.info('step '+str(step))
        traci.simulationStep()
        worker.doSimulationStep()
        step += 1

        if traci.vehicle.getIDCount() <= 0:
          break
    traci.close()
    sys.stdout.flush()

    statisticsValues.computeValues(worker.tls_of_evs, worker.blocking_tls_of_evs)

    return


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    optParser.add_option("--scenario", dest="scenario_folder", 
                          help="Scenario folder which the simulation will use", metavar="FILE")
    optParser.add_option("--withpreemption", action="store_true",
                         default=False, help="Indicates if preemption solution will be used")
    (options, args) = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    if not options.scenario_folder:
      sys.exit("You must specify the Scenario Folder using the '--scenario' option")

    Logger.set_globals(options.scenario_folder,'desenv',logging.INFO, options.withpreemption)

    logger = Logger('Runner').get()

    logger.info(options)

    #scenario = options.scenario

    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    #traci.start([sumoBinary, "-c", './' + scenario + '/osm.sumocfg',
    #                         "--tripinfo-output", './' + scenario + '/tripinfo.xml'])

    trip_file = 'tripinfo-'+ str(options.withpreemption) +'.xml'

    traci.start([sumoBinary, '-v','true','-c', options.scenario_folder+'/osm.sumocfg','--duration-log.statistics',
                             '--tripinfo-output', options.scenario_folder+'/' + trip_file])

    if options.withpreemption:
      server = WebhookServer('', 7000)
      server.start()                    

    run(options.withpreemption, options.scenario_folder, trip_file)   

    if options.withpreemption:
      server.stop()
