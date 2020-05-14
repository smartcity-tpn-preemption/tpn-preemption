from classes.preemption_strategy import PreemptionStrategy

from sumolib import checkBinary  # noqa
import traci  # noqa
import copy
import math
import sys

from .logger import Logger

class RfidPreemptionStrategy(PreemptionStrategy):

  def configure(self):
    self.__edges_with_preemption = [] 
    self.logger = Logger(self.__class__.__name__).get()
    self.logger.info('ok...')

  def execute_step(self,step,ev_entered_in_simulation):
    if ev_entered_in_simulation and self.ev in traci.vehicle.getIDList():
      self.conf.update_values()

      for edge_id in self.conf.edges_with_tl:
        if edge_id not in self.__edges_with_preemption:
          tl_current = self.conf.edges[edge_id]['tl']['name']

          distance_to_closest_tl = self.get_distance_to_tl(tl_current, edge_id)

          if distance_to_closest_tl <= self.options.distancedetection:
            self.open_tl_at_time_by_cycles(self.options.ncycles, edge_id, step)
            self.logger.info(self.commands)
            self.__edges_with_preemption.append(edge_id)

  def get_distance_to_tl(self,tl_current, tl_edge):
    if tl_current in traci.junction.getIDList():
      pos_ev_x, pos_ev_y = traci.vehicle.getPosition(self.ev)
      pos_tl_x,pos_tl_y = traci.junction.getPosition(tl_current)
      return traci.simulation.getDistance2D(pos_ev_x, pos_ev_y, pos_tl_x,pos_tl_y, False, False)
    
    if len(traci.vehicle.getNextTLS(self.ev)) > 0 and tl_current in traci.vehicle.getNextTLS(self.ev)[0][0]:
      return traci.vehicle.getNextTLS(self.ev)[0][2]

    return traci.vehicle.getDrivingDistance(self.ev,tl_edge,1.0)

  def instance_name(self):
    return super().instance_name() + \
            "_dd!"+str(self.options.distancedetection) + \
            "_nc!"+str(self.options.ncycles)