import requests
import sys
import zope.event
import uuid
import numpy

from default_worker import DefaultWorker
from spres_ev_util import SpresEVUtil

from sumolib import checkBinary  # noqa
import traci  # noqa

class PreemptionWorker(DefaultWorker):
    def preConfig(self):
      self._allowedEVsForTL = {}
      self._orderSent = {}

      self._preemptionsDone = {}

      self._tag = uuid.uuid4().hex      

      zope.event.subscribers.append(self.orderOfInterSCity)

      self._spresEV = SpresEVUtil(self._prefix, self._tag)

      self._spresEV.registerFakeTrafficLight()
      return True

      for ev in self._evList:
        if(not self._spresEV.createOrUpdate(ev)):
          self._logger.info('EV '+ ev + ' could not be registered')
          return False
        else:
          self._logger.info('EV '+ ev + 'registered in InterSCity')
      
      return True             

    def shouldNotifyTL(self, ev_id, tls_ids):
      mustNotifySet = set([])

      for tl_id in numpy.unique(tls_ids):
        if tl_id not in self._orderSent:
          self._orderSent[tl_id] = set([])

        if ev_id not in self._orderSent[tl_id]:
          self._logger.info('order of ' + str(ev_id) + ' sent to ' + str(tl_id) + ' (instance: ' + str(id(self)) + ')')
          self._orderSent[tl_id].add(ev_id)
          mustNotifySet.add(tl_id)

      self._logger.debug(mustNotifySet)
      self._logger.debug(len(mustNotifySet))
      self._logger.debug(list(mustNotifySet))

      self._spresEV.notify(ev_id, tls_ids, mustNotifySet)

    def actInBlockingTL(self, tl_id, ev_id, lane_index):
      # self._spresEV.doPreemption(tl_id, ev_id)

      if tl_id in self._allowedEVsForTL:
        currentProgram = traci.trafficlight.getProgram(tl_id)
        self._logger.debug(tl_id)
        self._logger.debug(traci.trafficlight.getRedYellowGreenState(tl_id))
        self._logger.debug(currentProgram)
        self._logger.debug(traci.trafficlight.getCompleteRedYellowGreenDefinition(tl_id))
        self._logger.debug(traci.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)[int(currentProgram)])

        allPrograms = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
        myProgram = [ program for program in allPrograms if program._subID == currentProgram ][0]
        self._logger.debug('program')
        self._logger.info(map((lambda ls: ls._phaseDef), myProgram._phases))

        self._logger.debug(dir(myProgram._phases[0]))
        self._logger.debug(myProgram._phases[0]._phaseDef)
        self._logger.info(tl_id)
        lights_sequence = map((lambda ls: ls._phaseDef[lane_index].upper()), myProgram._phases)
        self._logger.info(lane_index)
        self._logger.info(lights_sequence)
        currentPhaseIndex = traci.trafficlight.getPhase(tl_id)
        greenPhaseIndex = lights_sequence.index('G')
        safePhaseIndex = (greenPhaseIndex - 2) % len(lights_sequence)
        redPhaseIndex = (greenPhaseIndex - 1) % len(lights_sequence)
        self._logger.info(str(currentPhaseIndex) + ' ' + str(greenPhaseIndex) + ' ' + str(safePhaseIndex) + ' ' + str(redPhaseIndex) )

        if currentPhaseIndex not in [ safePhaseIndex, redPhaseIndex ]:
          # One preemption per vehicle on a specific traffic light
          if tl_id not in self._preemptionsDone:
            self._preemptionsDone[tl_id] = set([])

          if ev_id not in self._preemptionsDone[tl_id]:
            self._logger.info('preemption executed for ' + str(ev_id) + ' at ' + str(tl_id))
            traci.trafficlight.setPhase(tl_id, safePhaseIndex)
            self._preemptionsDone[tl_id].add(ev_id)
          else:
            self._logger.info('preemption NOT done (already got one) for ' + str(ev_id) + ' at ' + str(tl_id))


        # lane_index
        # find where is my Green phase
        # find to where should I hop

        # sys.exit(0)

    def orderOfInterSCity(self, event):
      self._logger.info('command received')
      self._logger.info(event)
      if 'tag' in event['command']['value']:
        tag = event['command']['value']['tag']

        if tag == self._tag:
          # This tag is from this run
          tl_id = event['command']['value']['tl']
          ev_id = event['command']['value']['target']
          command = event['command']['value']['order']

          if tl_id not in self._allowedEVsForTL:
            self._allowedEVsForTL[tl_id] = set([])

          if command == 'authorize' and ev_id not in self._allowedEVsForTL[tl_id]:
            self._allowedEVsForTL[tl_id].add(ev_id)
            self._logger.info(str(ev_id) + ' authorized for ' + str(tl_id) + ' (instance: ' + str(id(self)) + ')')

          if command == 'deny' and ev_id in self._allowedEVsForTL[tl_id]:
            self._allowedEVsForTL[tl_id].remove(ev_id)
            self._logger.info(str(ev_id) + ' denied for ' + str(tl_id) + ' (instance: ' + str(id(self)) + ')')

          self._logger.debug('current authorized:')
          self._logger.debug(self._allowedEVsForTL)
        else:
          self._logger.info('command tag ('+tag+') is different from my tag ('+ self._tag +'), ignoring command')
      else:
        self._logger.info('old command, tag is not in command, ignoring...')

    