from classes.preemption_strategy import PreemptionStrategy

from sumolib import checkBinary  # noqa
import traci  # noqa

from .logger import Logger

import sys
import math
import numpy as np
import random

import fuzzy.storage.fcl.Reader

class DjahelStrategy(PreemptionStrategy):

  def configure(self):
    self.logger = Logger(self.__class__.__name__).get()
    self._shouldInit = True
    self._lastLane = None
    self.fuzzysyst = fuzzy.storage.fcl.Reader.Reader().load_from_file("djahel.fcl")
    self.erp = 0    
    self.__edges_with_preemption = []
    self._original_lane_speed = {}
    self._perc_speed_increase = 1.5
    self._change_lane_time = 60*5
    self.rerouted = {}
    random.seed(self.options.seedsumo)

  def execute_before_step_simulation(self,step):
    super().execute_before_step_simulation(step)
    if self.ev in traci.vehicle.getIDList():
      should_exec = False
      if self.options.whencheck == 'start' and self._shouldInit:
        should_exec = True
      elif self.options.whencheck == 'lane' and traci.vehicle.getLaneID(self.ev) != self._lastLane:
        self._lastLane = traci.vehicle.getLaneID(self.ev)
        should_exec = True

      if should_exec:
        edges_speeds = []
        ols = []
        edges = traci.vehicle.getRoute(self.ev)
        index = traci.vehicle.getRouteIndex(self.ev)

        for i in range(index,len(edges)):
          edge = edges[i]
          edges_speeds.append(traci.edge.getLastStepMeanSpeed(edge))
          number_of_lanes = traci.edge.getLaneNumber(edge)

          for j in range(0,number_of_lanes):
            lane_j = edge+'_'+str(j)

            lengths = [traci.vehicle.getLength(veh) for veh in traci.lane.getLastStepVehicleIDs(lane_j)]

            if len(lengths) > 0 and traci.lane.getLength(lane_j) != 0:
              n_lane_j = len(lengths)
              avg_veh_length = np.mean(np.array(lengths))
              veh_gap = traci.vehicle.getMinGap(traci.lane.getLastStepVehicleIDs(lane_j)[0])
              lane_j_length = traci.lane.getLength(lane_j)

              ols.append((n_lane_j * (avg_veh_length + veh_gap))/(lane_j_length))
            else:
              ols.append(0)

        avs = np.mean(np.array(edges_speeds))
        ol = np.mean(np.array(ols))

        inputs = {
          'avs' : avs*3.6,
          'ol' : ol
        }

        output = {
          'cl' : 0
        }

        self.fuzzysyst.calculate(inputs,output)

        # cl -> [0-1): negligible [1-2): low [2-3):medium [3-4):high [4-5):critical
        self.erp = get_erp(output['cl'],self.options.el)

        if self.options.whencheck == 'start':
          self._shouldInit = False

  def execute_step(self,step,ev_entered_in_simulation):
    if self.ev in traci.vehicle.getIDList():
      self.exec_erp(step)          

    self.clear_lane_speed()
    self.correct_rerouted_vehicles()

  def exec_erp(self,step):
    if self.erp >= 1:
      #ERP 1 or higher - TL
      self.exec_tl(step)
    if self.erp >= 2:
      #ERP 2 or higher - SL
      self.exec_sl()
    if self.erp >= 3:
      #ERP 3 or higher - LC
      self.exec_lc()
    if self.erp >= 4:
      #ERP 4 or higher - RR
      self.exec_rr()
    if self.erp == 3 or self.erp == 5:
      #ERP 3 or ERP 5 - RL
      self.exec_rl()

  def correct_rerouted_vehicles(self):
    if len(self.rerouted) > 0:
      if self.ev not in traci.vehicle.getIDList():      
        for vehicle in self.rerouted:
          traci.vehicle.changeTarget(vehicle,self.rerouted[vehicle])
        self.rerouted = {}
      else:
        edges = traci.vehicle.getRoute(self.ev)
        to_del = []
        for vehicle in self.rerouted:
          if vehicle in traci.vehicle.getIDList():
            try:
              curr_index = traci.vehicle.getRouteIndex(vehicle)
              veh_edges = traci.vehicle.getRoute(vehicle)
              if curr_index >= len(veh_edges)-2:
                while True:
                  new_target = random.choice([e for e in self.conf.edges_to_reroute if e not in edges])
                  traci.vehicle.changeTarget(vehicle,new_target)
                  if traci.vehicle.isRouteValid(vehicle):
                    break
            except:
              self.logger.error('could not change route of vehicle {} to {}'.format(vehicle,new_target)) 
          else:
            to_del.append(vehicle)
        
        for veh in to_del:
          del self.rerouted[veh]

          
  def exec_rr(self):
    edges = traci.vehicle.getRoute(self.ev)
    index = traci.vehicle.getRouteIndex(self.ev)

    for i in range(index,len(edges)):
      edge = edges[i]
      vehicles_in_edge = [v for v in traci.edge.getLastStepVehicleIDs(edge) if v != self.ev ] 
      for vehicle in vehicles_in_edge:
        if vehicle not in self.rerouted and vehicle in traci.vehicle.getIDList():
          veh_edges = traci.vehicle.getRoute(vehicle)
          self.rerouted[vehicle] = veh_edges[-1]
          try:
            while True:
              new_target = random.choice([e for e in self.conf.edges_to_reroute if e not in edges])
              traci.vehicle.changeTarget(vehicle,new_target)
              if traci.vehicle.isRouteValid(vehicle):
                traci.vehicle.setColor(vehicle, (0,0,255))
                break
            self.statistics.vehicles_affected_by_ev.add(vehicle)
          except:
            self.logger.error('could not change route of vehicle {} to {}'.format(vehicle,new_target))

  
  def exec_rl(self):
    # DO NOTHING
    pass

  def exec_lc(self):
    leader = traci.vehicle.getLeader(self.ev)
    if leader:
      leader_name = leader[0]
      direction = 0
      if traci.vehicle.couldChangeLane(leader_name,1):
        direction = 1
      elif traci.vehicle.couldChangeLane(leader_name,-1):
        direction = -1
      if direction != 0:
        lane_index = traci.vehicle.getLaneIndex(leader_name) + direction
        road_id = traci.vehicle.getRoadID(leader_name)
        if lane_index >= 0 and lane_index < traci.edge.getLaneNumber(road_id):
          try:
            traci.vehicle.changeLane(leader_name,lane_index,self._change_lane_time)
            self.statistics.vehicles_affected_by_ev.add(leader_name)
            traci.vehicle.setColor(leader_name, (0,255,0))
          except:
            self.logger.error('{} could not change to lane index {} in {}'.format(leader_name,lane_index,road_id))

      


  def exec_tl(self,step):
    tls = traci.vehicle.getNextTLS(self.ev)

    #check preempted tls
    if len(tls) > 0:
      tl = tls[0][0]
      current_lane = traci.vehicle.getLaneID(self.ev)
      edge = traci.vehicle.getRoadID(self.ev)
      if current_lane in traci.trafficlight.getControlledLanes(tl) and \
        edge in self.conf.edges_with_tl and edge not in self.__edges_with_preemption:
        self.__edges_with_preemption.append(edge)
        self.open_tl_at_time_by_cycles(1, edge, step)

  def clear_lane_speed(self):
    if self.ev in traci.vehicle.getIDList():
      edges = traci.vehicle.getRoute(self.ev)
      index = traci.vehicle.getRouteIndex(self.ev)

      for i in range(0,index):
        edge = edges[i]
        number_of_lanes = traci.edge.getLaneNumber(edge)
        for i in range(0,number_of_lanes):
          lane_i = edge+'_'+str(i)

          if lane_i in self._original_lane_speed:
            traci.lane.setMaxSpeed(lane_i,self._original_lane_speed[lane_i])
            del self._original_lane_speed[lane_i]
    elif len(self._original_lane_speed) > 0:
      for lane in self._original_lane_speed:
        traci.lane.setMaxSpeed(lane,self._original_lane_speed[lane])
      self._original_lane_speed = {}

  def exec_sl(self):
    edges = traci.vehicle.getRoute(self.ev)
    index = traci.vehicle.getRouteIndex(self.ev)

    for i in range(index,len(edges)):
      edge = edges[i]
      number_of_lanes = traci.edge.getLaneNumber(edge)

      for i in range(0,number_of_lanes):
        lane_i = edge+'_'+str(i)

        if lane_i not in self._original_lane_speed:
          self._original_lane_speed[lane_i] = traci.lane.getMaxSpeed(lane_i)
          new_speed = self._original_lane_speed[lane_i]*self._perc_speed_increase
          traci.lane.setMaxSpeed(lane_i,new_speed)

  def instance_name(self):
    return super().instance_name() + \
            "_wc!"+str(self.options.whencheck) + \
            "_el!"+str(self.options.el)  


def get_erp(cl, el):
  erp = 0
  if cl < 1 and (el == 'low' or el == 'medium'):
    erp = 1
  elif cl < 1 and el == 'high':
    erp = 3
  elif (cl < 2 or cl < 3) and el == 'low':
    erp = 1
  elif (cl < 2 or cl < 3) and el == 'medium':
    erp = 2
  elif (cl < 2 or cl < 3) and el == 'high':
    erp = 3
  elif cl < 4 and (el == 'low' or el == 'medium'):
    erp = 4
  elif cl < 4 and el == 'high':
    erp = 5
  elif cl < 5 and el == 'low':
    erp = 4
  elif cl < 4 and (el == 'medium' or el == 'high'):
    erp = 5
  return erp