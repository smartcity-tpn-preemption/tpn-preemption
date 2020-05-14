from classes.preemption_strategy import PreemptionStrategy

from sumolib import checkBinary  # noqa
import traci  # noqa

from .logger import Logger
import math
from distutils.util import strtobool

class SmartcityCenteredStrategy(PreemptionStrategy):

  def configure(self):
    self.__k = 0
    self.__first_meet = True
    self.__remove_finished_preemptions = []
    self.__preemption_is_running = False
    self.__edge_cluster = []
    self.logger = Logger(self.__class__.__name__).get()
    self._reset_preemption = 0


  def execute_before_step_simulation(self,step):
    super().execute_before_step_simulation(step)

    if strtobool(self.options.sync):
      self.sync_tls(step) 

  def execute_step(self,step,ev_entered_in_simulation):
    if ev_entered_in_simulation and self.ev in traci.vehicle.getIDList():
      if self.conf.update_values():
        self.__k = 0

      if self.__k < len(self.conf.edges_with_tl):
        edge_id = self.conf.edges_with_tl[self.__k]
        tl_current = self.conf.edges[edge_id]['tl']['name']
        tl_info = self.conf.edges[edge_id]['tl']

        detection_distance = float(tl_info['s_detection'])
        vmax = float(tl_info['vmax'])

        distance_to_closest_tl = self.get_distance_to_tl(tl_current, edge_id)

        if self.__first_meet:
          self.__first_meet = False
          self.__edge_cluster = self.make_cluster()

        if distance_to_closest_tl > 0:
          self.logger.info('distance to tl: '+ str(distance_to_closest_tl))

          ev_acceleration = traci.vehicle.getAcceleration(self.ev)
          ev_speed = traci.vehicle.getSpeed(self.ev)

          self.logger.debug('acc '+str(ev_acceleration))
          self.logger.debug('speed '+str(ev_speed))

          if ev_acceleration == 0 and  ev_speed == 0 and self._reset_preemption > 0:
            #Should check timeout
            if step == self._reset_preemption:
              #RESET PREEMPTION!
              self.commands = {}
              self._reset_preemption = 0
          elif ev_acceleration == 0 and  ev_speed == 0 and self._reset_preemption  == 0:
            #Should start timeout
            self._reset_preemption = step + tl_info['ps_duration'][-1]
          elif ev_acceleration > 0 or ev_speed > 0:
            #EV is moving, we don't need to check timeout anymore
            self._reset_preemption = 0
          elif ((ev_acceleration < 0 and ev_speed < (vmax/self.options.thresholdfactor)) \
              or (distance_to_closest_tl <= detection_distance)) and not self.__preemption_is_running:  
            self.__preemption_is_running = True
            # start preemption
            self.logger.info('preemption is running now')

            self.logger.debug('vmax: '+str(tl_info['vmax']))

            self.get_commands(distance_to_closest_tl, tl_info, edge_id, step, self.options.speedfactor)
            self.logger.info(self.commands)

            for edge in self.__edge_cluster:
              # try to open next
              tl_info_next = self.conf.edges[edge]

              distance_to_next_tl = self.get_distance_to_tl(tl_info_next['tl']['name'], edge) 

              self.get_commands(distance_to_next_tl, tl_info_next['tl'], edge, step, self.options.speedfactor)

            self.logger.info(self.commands)                                                    

        current_distance = self.get_distance_to_tl(tl_current,edge_id)

        self.logger.info('current distance::: '+str(current_distance))

        if current_distance <= 0 and (len(traci.vehicle.getNextTLS(self.ev)) == 0 or traci.vehicle.getNextTLS(self.ev)[0][0] != tl_current):
          #restore phase if needed
          self.__preemption_is_running = False
          self.logger.debug('passed to '+ str(self.__k))

          self.__remove_finished_preemptions.append(edge_id)

          if len(self.__remove_finished_preemptions) > 1:
            edge_finished = self.__remove_finished_preemptions.pop(0)

            time_to_remove = []

            for time in self.commands:
              if edge_finished in self.commands[time]:
                del self.commands[time][edge_finished]
              if len(self.commands[time]) == 0:
                time_to_remove.append(time)

            for time_to_r in time_to_remove:
              del self.commands[time_to_r]

            if strtobool(self.options.sync):
              self.logger.debug('restore')

              self.tls_to_sync[edge_finished] = 1

          self.__first_meet = True
          self.__k = self.__k + 1

  def get_commands(self,distance_to_closest_tl, tl_info, edge_id, step, speedfactor):
    t_estimated = speedfactor*distance_to_closest_tl / float(tl_info['vmax'])
    y_duration = tl_info['y']['duration']
    r_duration = tl_info['r']['duration']
    g_duration = tl_info['g']['duration']
    cycle_quantity = math.ceil(((t_estimated-(y_duration+r_duration+g_duration))/g_duration)/2)+1

    if cycle_quantity <= 0 or tl_info['cluster']:
      cycle_quantity = 1

    # open tl

    self.open_tl_at_time_by_cycles(cycle_quantity+1, edge_id, 0 + step)

  def get_distance_to_tl(self,tl_current, tl_edge):
    if len(traci.vehicle.getNextTLS(self.ev)) > 0 and tl_current in traci.vehicle.getNextTLS(self.ev)[0][0]:
      return traci.vehicle.getNextTLS(self.ev)[0][2]

    distance = traci.vehicle.getDrivingDistance(self.ev,tl_edge,1.0)

    if distance < 0 and tl_current in traci.junction.getIDList():
        pos_tl_x,pos_tl_y = traci.junction.getPosition(tl_current)
        distance = traci.vehicle.getDrivingDistance2D(self.ev,pos_tl_x,pos_tl_y)

    return distance

  def make_cluster(self):
    #correct make cluster (consider other edges that dont have tl)

    j = self.__k+1
    tl_cluster = []
    edge = self.conf.edges_with_tl[self.__k]
    s_left = self.options.distancefactor*self.conf.edges[edge]['tl']['s_detection']

    while s_left > 0 and j < len(self.conf.edges_with_tl):
      edge_cluster = self.conf.edges_with_tl[j]
      distance_to_tl = self.get_distance_to_tl(self.conf.edges[edge_cluster]['tl']['name'], edge_cluster)
      self.logger.debug(str(s_left))
      if distance_to_tl <= s_left:
        s_left = s_left - distance_to_tl
        tl_cluster.append(edge_cluster)
        j = j + 1
      else:
        break

    self.logger.debug(str(tl_cluster))

    return tl_cluster

  def instance_name(self):
    return super().instance_name() + \
            "_sf!"+str(self.options.speedfactor)+ \
            "_df!"+str(self.options.distancefactor)+ \
            "_tf!"+str(self.options.thresholdfactor)+ \
            "_sync!"+str(self.options.sync)