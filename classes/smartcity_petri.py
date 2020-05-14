from classes.preemption_strategy import PreemptionStrategy
from classes.petri_util import PetriUtil

from snakes.nets import Substitution

import numpy as np
import random
import sys

from distutils.util import strtobool

from sumolib import checkBinary  # noqa
import traci  # noqa

class SmartcityPetriStrategy(PreemptionStrategy):
  def configure(self):
    self.pn = None
    self.last_tl = None
    random.seed(self.options.seedsumo)

    self.edge_of_tl = {}
    self.executed_states = []
    self.infinity = True
    self.was_cancelled = False
    #self.first_time = True
    self.time_cancel = None
    self.retry = None
    self.retry_number = 1
    self.skip_cluster = False
    self.local_cancelling = {}
    #self.conf.compute_adj = True

  def check_busy_wait(self,t):
    names = ['t21','t16','t19','t13','t22','t23','t6','t20','t10']
    for name in names:
      if name in t.name:
        return True    

  def execute_step(self,step,ev_entered_in_simulation):
    self.sync_tls(step)
    self.sync_tls_closed(step)    
    
    if ev_entered_in_simulation and self.ev in traci.vehicle.getIDList():

      edges = traci.vehicle.getRoute(self.ev)
      index = traci.vehicle.getRouteIndex(self.ev)

      current_tl_of_step = None
      while index < len(edges) and edges[index] not in self.conf.edges_with_tl:
        index = index + 1

      if index < len(edges):
        current_tl_of_step = self.conf.edges[edges[index]]['tl']['name'] 

      if self.pn == None or (self.retry is not None and step >= self.retry):
        if self.retry:
          self.retry_number += 1

        self.retry = None
        self.last_tl = current_tl_of_step

        self.executed_states = []
        self.edge_of_tl = {}        
        self.build_petri_net(step)

        for edge_id in self.conf.edges_with_tl:
          self.edge_of_tl[self.conf.edges[edge_id]['tl']['name']] = edge_id

        #for adj in self.adj_of_tl:
        #  edge_id = self.edge_of_tl[adj]
        #  for cl in traci.trafficlight.getControlledLinks(adj):
        #    if edge_id not in cl[0]:

      self.fire_transitions(step)

      if current_tl_of_step is not None:
        if current_tl_of_step != self.last_tl:
          self.skip_cluster = False

          #check crossed TL 
          self.check_crossing(step)

          self.rebuild_if_cancelled(step)

          self.last_tl = current_tl_of_step
        else:
          ev_speed = traci.vehicle.getSpeed(self.ev)
          ev_acc = traci.vehicle.getAcceleration(self.ev)

          tl_info = self.conf.edges[self.edge_of_tl[current_tl_of_step]]['tl']
          lane_in = tl_info['lane_in']
          occupancy = traci.lane.getLastStepOccupancy(lane_in)
          mean_speed = traci.lane.getLastStepMeanSpeed(lane_in)
          lights = traci.trafficlight.getRedYellowGreenState(current_tl_of_step)
          light_index = tl_info['link_index']

          if ev_speed == 0 and ev_acc == 0 and lights[light_index].upper() == 'G' and (\
             (occupancy > 0 and mean_speed <= 0) or \
              (self.get_distance_to_tl(current_tl_of_step,self.edge_of_tl[current_tl_of_step]) <= 2) ):
            if self.local_cancelling:
              trans_name = '{}_{}'.format('t8',current_tl_of_step)
              t = self.pn.transition(trans_name)
              if t.enabled(Substitution()):
                t.fire(Substitution())
                self.logger.info('firing {} on {}, local cancelling...'.format(trans_name,current_tl_of_step))
            else:
              t = self.pn.transition('t17')
              if t.enabled(Substitution()):
                t.fire(Substitution())
                self.was_cancelled = True
                self.time_cancel = None
                self.retry = step + self.retry_number*150
                self.local_cancelling = {}
                self.logger.info('firing t17 because {}, cancelling...'.format(current_tl_of_step))                 
      elif self.last_tl is not None:
        self.check_crossing(step)
        self.last_tl = None


      if not self.was_cancelled:
        self.check_cancelling(step,current_tl_of_step)
          #print('{} fired. Current marking: {}'.format(t.name,self.pn.get_marking()))                     
          
        #lane_of_tl = 
        #edge_id = self.edge_of_tl[current_tl_of_step] 

        #print('lane mean speed: {}'.format(traci.lane.getLastStepMeanSpeed(lane_id)))

    elif self.pn is not None:
      if 'p21' not in self.pn.get_marking():
        t = self.pn.transition('t17')
        if t.enabled(Substitution()):
          t.fire(Substitution())
          self.was_cancelled = True
          self.retry = None
      else:        
        self.fire_transitions(step)
        if self.last_tl is not None:
          self.check_crossing(step)
          self.last_tl = None

  def fire_transitions(self, step):
    if self.pn is not None:
      self.pn.time(step)

      enabled_trans = [t for t in self.pn.transition() if 't8' not in t.name and 't17' not in t.name and t.enabled(Substitution()) and not self.check_busy_wait(t)]

      #markings = self.pn.get_marking()

      for t in random.sample(enabled_trans, len(enabled_trans)):
        if not t.enabled(Substitution()):
          continue

        #if 't2_' in t.name:
        #  print(t.name)

        t.fire(Substitution())
        #if not self.check_busy_wait(t):
        #  print('{} fired. Current marking: {}'.format(t.name,self.pn.get_marking()))
        #  print()

        for m in self.pn.get_marking():
          if 'p3_' in m and m not in self.executed_states:
            self.executed_states.append(m)
            splitted_name = m.split('_')
            edge_id =  self.edge_of_tl['_'.join(splitted_name[1:len(splitted_name)])]
            self.open_tl_at_time_by_cycles(1,edge_id,step)          

          #do actions (close adjacents)
          #if 'p4_' in m:
          #  splitted_name = m.split('_')
          #  edge_id =  self.edge_of_tl['_'.join(splitted_name[1:len(splitted_name)])]

          #  for tl in self.conf.edges[edge_id]['tl']['adjs']:
          #    self.close_tl_at_time_by_cycles(tl,self.conf.edges[edge_id]['tl']['adjs'][tl],step)

          if 'p6_' in m and m not in self.executed_states:
            self.executed_states.append(m)
            splitted_name = m.split('_')
            tl_to_restore = '_'.join(splitted_name[1:len(splitted_name)])
            edge_id = self.edge_of_tl[tl_to_restore]
            self.tls_to_sync[edge_id] = 1

            for tl in self.conf.edges[edge_id]['tl']['adjs']:
              self.tls_to_sync_closed[tl] = {}
              self.tls_to_sync_closed[tl]['state'] = 1
              self.tls_to_sync_closed[tl]['info'] = self.conf.edges[edge_id]['tl']['adjs'][tl]


  def check_cancelling(self, step, current_tl_of_step):
    can_cancel = False

    #if self.first_time:
    #  increment = 7
    #else:
    increment = 3

    if strtobool(self.options.localcancelling):
      for other_edge in self.conf.edges_with_tl:
        other_tl_info = self.conf.edges[other_edge]['tl']
        other_tl_name = other_tl_info['name']
        other_lane_in = other_tl_info['lane_in']
        if '{}_{}'.format('p3',other_tl_name) in self.executed_states:
          occupancy_other = traci.lane.getLastStepOccupancy(other_lane_in)
          mean_speed_other = traci.lane.getLastStepMeanSpeed(other_lane_in)
          lights_other = traci.trafficlight.getRedYellowGreenState(other_tl_name)
          light_index_other = other_tl_info['link_index']

          if lights_other[light_index_other].upper() == 'G' and occupancy_other > 0 and mean_speed_other <= 0:
            if other_tl_name not in self.local_cancelling:
              self.local_cancelling[other_tl_name] = step + increment
            elif step >= self.local_cancelling[other_tl_name]:
              next_index = self.conf.edges_with_tl.index(other_edge) +1

              should_restore = True

              if next_index < len(self.conf.edges_with_tl):
                next_edge = self.conf.edges_with_tl[next_index]
                next_tl_info = self.conf.edges[next_edge]['tl']
                next_tl_name = next_tl_info['name']
                next_lane_in = next_tl_info['lane_in']
                if '{}_{}'.format('p3',next_tl_name) in self.executed_states:
                  occupancy_next = traci.lane.getLastStepOccupancy(next_lane_in)
                  lights_next = traci.trafficlight.getRedYellowGreenState(next_tl_name)
                  light_index_next = next_tl_info['link_index']
                  if lights_next[light_index_next].upper() == 'G' and occupancy_next == 0:
                    next_trans_name = '{}_{}'.format('t8',next_tl_name)
                    t = self.pn.transition(next_trans_name)
                    if t.enabled(Substitution()):
                      t.fire(Substitution())
                      self.logger.info('firing NEXT {} because NEXT {} previous {}, local cancelling...'.format(next_trans_name,
                                        next_tl_name,other_tl_name))
                      self.local_cancelling[other_tl_name] = step + 4*increment
                      should_restore = False                       

              if should_restore:
                trans_name = '{}_{}'.format('t8',other_tl_name)
                t = self.pn.transition(trans_name)
                if t.enabled(Substitution()):
                  t.fire(Substitution())
                  self.logger.info('firing {} because {}, local cancelling...'.format(trans_name,other_tl_name))          
                del self.local_cancelling[other_tl_name]
          elif other_tl_name in self.local_cancelling:
            del self.local_cancelling[other_tl_name]

    if current_tl_of_step is not None and '{}_{}'.format('p3',current_tl_of_step) in self.executed_states:
      edge_id = self.edge_of_tl[current_tl_of_step]    
      tl_info = self.conf.edges[edge_id]['tl']

      edge_in = self.edge_of_tl[current_tl_of_step]
      lane_in = tl_info['lane_in']
      occupancy = traci.lane.getLastStepOccupancy(lane_in)
      mean_speed = traci.lane.getLastStepMeanSpeed(lane_in)
      lights = traci.trafficlight.getRedYellowGreenState(current_tl_of_step)
      light_index = tl_info['link_index']

      if lights[light_index].upper() == 'G' and occupancy > 0 and mean_speed <= 0 and not strtobool(self.options.localcancelling):
        if self.time_cancel is None:
          self.time_cancel = step + increment
        elif self.time_cancel >= step:
          can_cancel = True
        else:
          self.time_cancel = None
      else:
        edge_ev = traci.vehicle.getRoadID(self.ev)
        ev_speed = traci.vehicle.getSpeed(self.ev)
        ev_acc = traci.vehicle.getAcceleration(self.ev)

        if (':' not in edge_ev and edge_ev != edge_in) and ev_speed == 0 and ev_acc <= 0 and \
            ('cluster' in current_tl_of_step or 'joinedS' in current_tl_of_step) and not self.skip_cluster:
          controlled_links = traci.trafficlight.getControlledLinks(current_tl_of_step)
          lane_ins = [tup[0][0] for tup in controlled_links if edge_ev in tup[0][0]]
          if len(lane_ins) > 0:       
            edge_id = self.edge_of_tl[current_tl_of_step]
            self.tls_to_sync[edge_id] = 1
            self.skip_cluster = True
          elif ev_speed == 0 and ev_acc == 0 and self.time_cancel is None:
              self.time_cancel = step + increment
        elif ev_speed == 0 and ev_acc == 0:
          if self.time_cancel is None:
            self.time_cancel = step + increment

          edge_ev = traci.vehicle.getRoadID(self.ev)
          lane_ev = traci.vehicle.getLaneID(self.ev)
          occupancy_lane_ev = traci.lane.getLastStepOccupancy(lane_ev)
          mean_speed_lane_ev = traci.lane.getLastStepMeanSpeed(lane_ev)

          controlled_links = traci.trafficlight.getControlledLinks(current_tl_of_step)
          edge_without_hashtag_splitted = edge_ev.split('#')
          edge_without_hashtag = '_'.join(edge_without_hashtag_splitted[0:len(edge_without_hashtag_splitted)-1])
          lane_ins = [tup[0][0] for tup in controlled_links if edge_without_hashtag in tup[0][0]]
          if len(lane_ins) > 0 and occupancy_lane_ev > 0 and mean_speed_lane_ev <= 0.25:
            can_cancel = True
        elif self.time_cancel is not None:
            self.time_cancel = None

      if can_cancel or (self.time_cancel is not None and self.time_cancel >= step):
        t = self.pn.transition('t17')
        if t.enabled(Substitution()):
          t.fire(Substitution())
          self.was_cancelled = True
          self.time_cancel = None
          self.retry = step + self.retry_number*150
          self.local_cancelling = {}
          self.logger.info('firing t17 because {}, cancelling...'.format(current_tl_of_step))          


    #g_index = self.conf.edges[edge_id]['tl']['g']['index']
    #c_lanes = traci.trafficlight.getControlledLanes(current_tl_of_step)
    
    #if len(c_lanes) > 0 and g_index < len(c_lanes):
    #check cancel condition
    #ev_acceleration = traci.vehicle.getAcceleration(self.ev)
    #ev_speed = traci.vehicle.getSpeed(self.ev)
    #lane_id = traci.vehicle.getLaneID(self.ev)
    #lane_of_tl = c_lanes[g_index]

    #avg_speed_lane_ev = traci.lane.getLastStepMeanSpeed(lane_id)

    #avg_speed_lane_tl = traci.lane.getLastStepMeanSpeed(lane_of_tl)
    #if self.first_time and ev_acceleration == 0 and ev_speed == 0:
    #  self.first_time = False
    #elif ev_acceleration <= 0 and ev_speed <= 1.25 and avg_speed_lane_ev <= 1.25 and traci.lane.getLastStepOccupancy(lane_id) >= 0.5: #and avg_speed_lane_tl <= 1.25:
    #  t = self.pn.transition('t17')
    #  if t.enabled(Substitution()):
    #    t.fire(Substitution())
    #    self.was_cancelled = True
    #else:
    #  edges = traci.vehicle.getRoute(self.ev)
    #  index = traci.vehicle.getRouteIndex(self.ev)
    #  for i in range(index+1,len(edges)):
    #    edge_id = edges[i]
    #    if edge_id in self.conf.edges_with_tl:
    #      tl_id = self.conf.edges[edge_id]['tl']['name']
    #      if '{}_{}'.format('p3',tl_id) in self.executed_states and traci.edge.getLastStepMeanSpeed(edge_id) <= 1.25 and \
    #        traci.edge.getLastStepOccupancy(edge_id) >= 0.75:
    #          t = self.pn.transition('t17')
    #          if t.enabled(Substitution()):
    #            t.fire(Substitution())
    #            self.was_cancelled = True          

        #print('{} fired. Current marking: {}'.format(t.name,self.pn.get_marking()))                     

  def check_crossing(self, step):
    #check crossed TL
    if self.last_tl is not None: 
      trans_name = '{}_{}'.format('t8',self.last_tl)
      t = self.pn.transition(trans_name)
      if t.enabled(Substitution()):
        t.fire(Substitution())
        self.retry_number = 1
        #self.first_time = False
        #print('{} fired. Current marking: {}'.format(t.name,self.pn.get_marking()))

  def rebuild_if_cancelled(self, step):
    if self.was_cancelled:
      self.was_cancelled = False
      self.executed_states = []
      self.edge_of_tl = {}        
      self.build_petri_net(step)

      for edge_id in self.conf.edges_with_tl:
        self.edge_of_tl[self.conf.edges[edge_id]['tl']['name']] = edge_id

  def build_petri_net(self, step):
    #self.first_time = True
    edges = traci.vehicle.getRoute(self.ev)
    index = traci.vehicle.getRouteIndex(self.ev)

    edges_speeds = []
    density_lanes = []
    time_to_open_tls = {}
    avg_vmax = []
    for i in range(index,len(edges)):
      edge = edges[i]
      edges_speeds.append(traci.edge.getLastStepMeanSpeed(edge))        
      #n_lanes = traci.edge.getLaneNumber(edge)
      density_lanes.append(traci.edge.getLastStepOccupancy(edge))

      #for j in range(0,n_lanes):
      #  lane_j = edge+'_'+str(j)

      #  density_lanes.append(traci.lane.getLastStepOccupancy(lane_j))

        #lengths = [traci.vehicle.getLength(veh) for veh in traci.lane.getLastStepVehicleIDs(lane_j)]

        #if len(lengths) > 0 and traci.lane.getLength(lane_j) != 0:
        #  n_lane_j = len(lengths)
        #  avg_veh_length = np.mean(np.array(lengths))
        #  veh_gap = traci.vehicle.getMinGap(traci.lane.getLastStepVehicleIDs(lane_j)[0])
        #  lane_j_length = traci.lane.getLength(lane_j)

        #  density_lanes.append((n_lane_j * (avg_veh_length + veh_gap))/(lane_j_length))
        #else:
        #  density_lanes.append(0)

      if edge in self.conf.edges_with_tl:
        tl_info = self.conf.edges[edge]['tl']
        distance_to_tl = self.get_distance_to_tl(tl_info['name'],edge)
        num_lanes = traci.edge.getLaneNumber(edge)
        for edge_lane in range(num_lanes):
          lane_name = '{}_{}'.format(edge,edge_lane)
          avg_vmax.append(traci.lane.	getMaxSpeed(lane_name))
        #vmax = tl_info['vmax']
        vmax = np.mean(np.array(avg_vmax))
        flush_time = tl_info['y']['duration'] + tl_info['r']['duration']
        avg_speed = np.mean(np.array(edges_speeds))
        #ev_speed = traci.vehicle.getSpeed(self.ev)        

        if distance_to_tl / vmax <= 0 or avg_speed <= 0:
          #open NOW
          time_to_open_tls[tl_info['name']] = step
        else:
          density_of_path = np.mean(np.array(density_lanes))
          opening_time = (((distance_to_tl/vmax)- 3 - flush_time)*(1-density_of_path))
          if opening_time < 0:
            opening_time = 1
          time_to_open_tls[tl_info['name']] = step + opening_time

    self.pn = PetriUtil().build_petri_net(self.conf,edges,index,time_to_open_tls)
    #print(self.pn)

  def get_distance_to_tl(self,tl_current, tl_edge):
    if len(traci.vehicle.getNextTLS(self.ev)) > 0 and tl_current in traci.vehicle.getNextTLS(self.ev)[0][0]:
      return traci.vehicle.getNextTLS(self.ev)[0][2]

    distance = traci.vehicle.getDrivingDistance(self.ev,tl_edge,1.0)

    if distance < 0 and tl_current in traci.junction.getIDList():
        pos_tl_x,pos_tl_y = traci.junction.getPosition(tl_current)
        distance = traci.vehicle.getDrivingDistance2D(self.ev,pos_tl_x,pos_tl_y)

    return distance

  def instance_name(self):
    return super().instance_name() + \
            "_lc!"+str(self.options.localcancelling)   
