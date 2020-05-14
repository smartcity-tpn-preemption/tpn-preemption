from sumolib import checkBinary  # noqa
import traci  # noqa

from .logger import Logger

import math
import sys
import copy

class PreemptionStrategy(object):
  def __init__(self, opt):
    self.options = opt
    self.restore_tls = {}
    self.commands = {}
    self.commands_to_close = {}
    self.tls_to_sync = {}
    self.tls_to_sync_closed = {}
    self.infinity = False

  def sync_tls_closed(self, step):
    remove_from_sm = []   

    for tl_to_sync in self.tls_to_sync_closed:
      tl_info_removed = self.tls_to_sync_closed[tl_to_sync]['info']
      state = self.tls_to_sync_closed[tl_to_sync]['state']

      time_in_program = step%float(tl_info_removed['ps_duration'][-1])
      total_phases = len(tl_info_removed['ps_duration'])

      real_index = 0
      while tl_info_removed['ps_duration'][real_index] < time_in_program:
        real_index = real_index + 1

      self.tls_to_sync_closed[tl_to_sync]['state'] = self.change_state(state, tl_to_sync, \
                                                        real_index, tl_to_sync, remove_from_sm, total_phases, \
                                                        tl_info_removed, time_in_program, step)

    for tl in remove_from_sm:
      del self.tls_to_sync_closed[tl]

      if self.infinity:
        steps = [s for s in self.commands_to_close if tl in self.commands_to_close[s]]
        for s in steps:
          del self.commands_to_close[s][tl]                                                                        


  def sync_tls(self, step):
    remove_from_sm = []

    for edge_to_sync in self.tls_to_sync:
      tl_info_removed = self.conf.edges[edge_to_sync]['tl']
      tl_name = tl_info_removed['name']

      time_in_program = step%float(tl_info_removed['ps_duration'][-1])
      total_phases = len(tl_info_removed['ps_duration'])
      self.logger.debug('time in program: '+str(time_in_program))

      real_index = 0
      while tl_info_removed['ps_duration'][real_index] < time_in_program:
        real_index = real_index + 1


      # check color state
      self.tls_to_sync[edge_to_sync] = self.change_state(self.tls_to_sync[edge_to_sync], tl_name, \
                                                        real_index, edge_to_sync, remove_from_sm, total_phases, \
                                                        tl_info_removed, time_in_program, step)


    for edge in remove_from_sm:
      del self.tls_to_sync[edge]

      if self.infinity:
        steps = [s for s in self.commands if edge in self.commands[s]]
        for s in steps:
          del self.commands[s][edge]

  def change_state(self, state, tl_name, real_index, obj_to_sync, remove_from_sm, total_phases, tl_info_removed, time_in_program, step):
    current_light, real_light = self.get_colors(tl_name, tl_info_removed, real_index)
    current_index = traci.trafficlight.getPhase(tl_name)
    current_time_left = int(traci.trafficlight.getNextSwitch(tl_name)) - step
    real_time_left = tl_info_removed['ps_duration'][real_index] - time_in_program

    if state == 1:
      if current_light == 'r':
        if real_light in ['r','g']:
          # L1 = R and L2 in (R,G) noqa
          traci.trafficlight.setPhase(tl_name,real_index)
          traci.trafficlight.setPhaseDuration(tl_name,real_time_left)
          remove_from_sm.append(obj_to_sync)
          return 0
        else:
          # L1 = R and L2 = Y noqa
          traci.trafficlight.setPhase(tl_name,(real_index+1)%total_phases)
          if self.infinity:
            current_time_left = 0
          traci.trafficlight.setPhaseDuration(tl_name,current_time_left+traci.trafficlight.getPhaseDuration(tl_name))
          remove_from_sm.append(obj_to_sync)
          return 0
      elif current_light == 'y':
          # L1 = Y noqa
          return 8
      elif current_light == 'g':
        next_green_light = (real_index+1)%total_phases
        time_to_check = real_time_left
        if real_light == 'y':
          time_to_check = time_to_check + tl_info_removed['durations'][(real_index+1)%total_phases]              
          next_green_light = (next_green_light+1)%total_phases

        if current_index == real_index:
          # L1 = G and L1 = L2 noqa
          traci.trafficlight.setPhaseDuration(tl_name,real_time_left)
          remove_from_sm.append(obj_to_sync)
          return 0
        elif real_light in ['r','y'] and next_green_light == current_index and current_time_left >= time_to_check:
          # L1 = G and L2 in (R,Y) and next(G,L2) = L1 and (timeLeft(L1) >= timeLeft(L2) + duration(next(R,L2)) if L2 = Y or timeLeft(L2))
          green_phase_duration = tl_info_removed['durations'][current_index]
          traci.trafficlight.setPhase(tl_name,current_index)
          traci.trafficlight.setPhaseDuration(tl_name,green_phase_duration+time_to_check)
          remove_from_sm.append(obj_to_sync)
          return 0
        else:
          # L1 = G and L2 doesn't matter now
          lights = traci.trafficlight.getRedYellowGreenState(tl_name)
          self.change_y_phase(lights, tl_name, tl_info_removed, step)
          return 8
    elif state == 8:
      if not self.infinity and int(traci.trafficlight.getNextSwitch(tl_name)) - step <= 1:
        return 1
      elif current_light == 'r':
        return 1
      else:
        return 8

  def setup(self, configuration, stats, evehicle):
    self.conf = configuration
    self.statistics = stats
    self.ev = evehicle
    self.logger = Logger(self.__class__.__name__).get()
    self.logger.info('Initiating')        

  def configure(self):
    pass

  def get_colors(self,tl_current, tl_info, index):
    current_lights = traci.trafficlight.getRedYellowGreenState(tl_current)
    if 'g' in current_lights.lower():
      current_light = 'g'
    elif 'y' in current_lights.lower():
      current_light = 'y'
    else:
      current_light = 'r'

    real_lights = tl_info['phases'][index]
    if 'g' in real_lights.lower():
      real_light = 'g'
    elif 'y' in real_lights.lower():
      real_light = 'y'
    else:
      real_light = 'r'

    return current_light, real_light

  def actuate_close(self, step, command):
    tl = command['name']
    if command['color'] == 'y':
      lights = traci.trafficlight.getRedYellowGreenState(tl)

      if lights.lower().count('r') == len(lights):
        traci.trafficlight.setPhaseDuration(tl,1000000)
        return

      if 'g' in lights.lower():
        self.change_y_phase(lights, tl, command['info'], step)

      lights = traci.trafficlight.getRedYellowGreenState(tl)

      if 'y' in lights.lower():
        next_switch = int(traci.trafficlight.getNextSwitch(tl))

        if next_switch+1 not in self.commands_to_close:
          self.commands_to_close[next_switch+1] = {}

        if tl not in self.commands_to_close[next_switch+1]:
          self.commands_to_close[next_switch+1][tl] = {}
          self.commands_to_close[next_switch+1][tl]['color'] = 'r'
          self.commands_to_close[next_switch+1][tl]['name'] = tl
          self.commands_to_close[next_switch+1][tl]['info'] = command['info']
      else:
        if self.infinity:
          traci.trafficlight.setPhaseDuration(tl,1000000)
    elif self.infinity:
        traci.trafficlight.setPhaseDuration(tl,1000000)      

  def actuate(self,step, edge):
    tl = self.conf.edges[edge]['tl']['name']
    if self.commands[step][edge]['color'] == 'y':
      self.logger.info("current phase of "+str(tl)+": "+str(traci.trafficlight.getPhase(tl)))

      lights = traci.trafficlight.getRedYellowGreenState(tl)
      if lights.lower().count('r') == len(lights):
        traci.trafficlight.setPhase(tl,self.conf.edges[edge]['tl']['g']['index'])
        if self.infinity:
          traci.trafficlight.setPhaseDuration(tl,1000000)
        return

      my_green_phase = False

      if traci.trafficlight.getPhase(tl) == self.conf.edges[edge]['tl']['g']['index']:
        my_green_phase = True
        if self.infinity:
          traci.trafficlight.setPhase(tl,self.conf.edges[edge]['tl']['g']['index'])
          traci.trafficlight.setPhaseDuration(tl,1000000)
          return

      if not my_green_phase:
        self.change_y_phase(lights, tl, self.conf.edges[edge]['tl'], step)

      next_switch = int(traci.trafficlight.getNextSwitch(tl))

      cycles = self.commands[step][edge]['cycles']
      red_phase_duration = int(self.conf.edges[edge]['tl']['r']['duration'])
      green_phase_duration = int(self.conf.edges[edge]['tl']['g']['duration'])

      if not my_green_phase:
        next_times = next_switch+red_phase_duration
      else:
        next_times = next_switch

      for c in range(1,int(cycles)+1):
        if next_times not in self.commands:
          self.commands[next_times] = {}

        if edge not in self.commands[next_times]:
          self.commands[next_times][edge] = {}

        self.commands[next_times][edge]['color'] = 'g'              
        next_times = next_times + green_phase_duration
    else:
      self.logger.debug(tl+' '+ str(self.conf.edges[edge]['tl'][self.commands[step][edge]['color']]['index']))
      self.logger.debug(traci.trafficlight.getCompleteRedYellowGreenDefinition(tl))
      traci.trafficlight.setPhase(tl,self.conf.edges[edge]['tl'][self.commands[step][edge]['color']]['index'])
      if self.infinity:
        traci.trafficlight.setPhaseDuration(tl,1000000)
      
  def change_y_phase(self, lights, tl, tl_info, step):
    had_green = False
    first_light = lights

    while 'g' in lights or 'G' in lights:
      had_green = True
      next_phase = (traci.trafficlight.getPhase(tl) + 1) % len(tl_info['phases'])
      traci.trafficlight.setPhase(tl,next_phase)
      lights = traci.trafficlight.getRedYellowGreenState(tl)

    if had_green:
      new_lights = []
      for char in first_light:
        if 'g' == char or 'G' == char:
          new_lights.append('y')
        else:
          new_lights.append(char)

      new_lights = "".join(new_lights)

      if lights != new_lights:
        if not tl in self.restore_tls:
          self.restore_tls[tl] = {}

        self.restore_tls[tl]['after'] = int(traci.trafficlight.getNextSwitch(tl))
        self.restore_tls[tl]['lights'] = lights
        self.restore_tls[tl]['phase'] = next_phase
        nswitch = int(traci.trafficlight.getNextSwitch(tl)) - step          
        program = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)[0]
        self.restore_tls[tl]['program'] = program
        new_program = copy.deepcopy(program)
        self.restore_tls[tl]['total_phases'] = len(new_program.phases)

        self.logger.debug(new_program)

        new_program.phases[next_phase].state = new_lights
        traci.trafficlight.setCompleteRedYellowGreenDefinition(tl,new_program)
        self.logger.debug('installed program: '+str(traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)))
        traci.trafficlight.setProgram(tl,'0')
        traci.trafficlight.setPhase(tl,next_phase)
        traci.trafficlight.setPhaseDuration(tl,nswitch)
        self.logger.debug('was toogled')      

  def execute_before_step_simulation(self,step):
    del_restore = []
    for tl in self.restore_tls:
      phase = int(traci.trafficlight.getPhase(tl))
      self.logger.info('to restore: tl '+str(tl)+' current phase: '+str(phase))
      self.logger.info('lights now: '+str(traci.trafficlight.getRedYellowGreenState(tl)))
      self.logger.info('next switch: '+str(traci.trafficlight.getNextSwitch(tl)))

      if step >= self.restore_tls[tl]['after']:
        nswitch = int(traci.trafficlight.getNextSwitch(tl)) - step
        backup_program = self.restore_tls[tl]['program']
        traci.trafficlight.setCompleteRedYellowGreenDefinition(tl,backup_program)
        traci.trafficlight.setProgram(tl,'0')
        traci.trafficlight.setPhase(tl,phase)
        traci.trafficlight.setPhaseDuration(tl,nswitch)
        del_restore.append(tl)          

    for d in del_restore:
      del self.restore_tls[d]

    if len(self.commands) > 0 and step in self.commands:
      for edge in self.commands[step]:
        self.actuate(step, edge)

      del self.commands[step]

    if len(self.commands_to_close) > 0 and step in self.commands_to_close:
      for tl in self.commands_to_close[step]:
        self.actuate_close(step,self.commands_to_close[step][tl])

      del self.commands_to_close[step]      

  def open_tl_at_time_by_cycles(self,cycle_quantity, edge_id, t):
    self.logger.info('when '+str(t))

    t_key = int(math.floor(t)+1)

    if t_key not in self.commands:
      self.commands[t_key] = {}

    self.commands[t_key][edge_id] = {}

    self.commands[t_key][edge_id]['cycles'] = cycle_quantity
    self.commands[t_key][edge_id]['color'] = 'y'

  def close_tl_at_time_by_cycles(self, tl, tl_info, t):
    t_key = int(math.floor(t)+1)

    if t_key not in self.commands_to_close:    
       self.commands_to_close[t_key] = {}

    self.commands_to_close[t_key][tl] = {}

    self.commands_to_close[t_key][tl]['name'] = tl
    self.commands_to_close[t_key][tl]['color'] = 'y'       
    self.commands_to_close[t_key][tl]['info'] = tl_info

  def execute_step(self,step,ev_entered_in_simulation):
    pass

  def finish(self):
    self.commands = {}

  def instance_name(self):
    return "alg!"+self.options.algorithm+"_ev!"+str(self.options.ev)+"_seed!"+str(self.options.seedsumo)