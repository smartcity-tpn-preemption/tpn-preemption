import os.path
import sys
from os import listdir
from os.path import isfile, join
import json
import numpy
import optparse
import sys
from statistics import mean
import matplotlib.pyplot as plt

def do_work(command): 
  results = command['results']
  method = command['method']
  basefolder = command['basefolder']
  location = command['location']
  instance = command['instance']
  jsonfile = command['jsonfile']
  prefix = command['prefix']

  results = dict({})

  if method == 'append' or method == 'override':
    if method == 'override' or location not in results:
      results[location] = {}

    i = instance

    current_base_folder = os.path.join(basefolder,location)
    current_base_folder = os.path.join(current_base_folder,'{}-{}'.format(location,i))
    current_base_folder = os.path.join(current_base_folder,'results')
    current_base_folder = os.path.join(current_base_folder,prefix)

    if method == 'override' or i not in results[location]:
      results[location][i] = {}

    if os.path.exists(current_base_folder):
      f = jsonfile
      name_parts = f.split('.json')[0].split('_')
      car_density = 'Car density'

      alg_name = name_parts[0].split('!')[1]
      ev = name_parts[1].split('!')[1]
      seed = name_parts[2].split('!')[1]

      if method == 'override' or alg_name not in results[location][i]:
        results[location][i][alg_name] = {}
      
      args_name = '_'.join(name_parts[3:len(name_parts)])

      if method == 'override' or args_name not in results[location][i][alg_name]:
        results[location][i][alg_name][args_name] = {}

      if method == 'override' or ev not in results[location][i][alg_name][args_name]:
        results[location][i][alg_name][args_name][ev] = {}

      was_empty = False
      if seed not in results[location][i][alg_name][args_name][ev]:
        was_empty = True
        results[location][i][alg_name][args_name][ev][seed] = {}
        results[location][i][alg_name][args_name][ev][seed]['ttt-ev'] = {}
        results[location][i][alg_name][args_name][ev][seed]['timeloss-ev'] = {}
        results[location][i][alg_name][args_name][ev][seed]['ttt-other'] = {}
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other'] = {}
        results[location][i][alg_name][args_name][ev][seed]['ttt-other-var'] = {}
        results[location][i][alg_name][args_name][ev][seed]['ttt-other-std'] = {}
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-var'] = {}
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-std'] = {}
        results[location][i][alg_name][args_name][ev][seed]['n_vehicles'] = {}
        results[location][i][alg_name][args_name][ev][seed]['avg_car_density'] = {}
        results[location][i][alg_name][args_name][ev][seed]['ev_was_teleported'] = {}

      if method == 'override' or (method == 'append' and was_empty):
        file_tmp = open(os.path.join(current_base_folder,f),'r')
        try:
          print('processing {}'.format(os.path.join(current_base_folder,f)))
          partial_data = json.loads(file_tmp.read())
          print('{} processed'.format(os.path.join(current_base_folder,f)))
        except:
          #print('Error in {}'.format(os.path.join(current_base_folder,f)))
          #traceback.print_exc()
          #raise e            
          file_tmp.close()
          file_tmp = open(command['errorfile'],'a+')
          file_tmp.write('{}\n'.format(os.path.join(current_base_folder,f)))
          file_tmp.close()
          return {}
        file_tmp.close()

        results[location][i][alg_name][args_name][ev][seed]['ttt-ev'] = float(partial_data['summary']['ttt-ev'])
        results[location][i][alg_name][args_name][ev][seed]['timeloss-ev'] = float(partial_data['summary']['timeloss-ev'])
        results[location][i][alg_name][args_name][ev][seed]['ttt-other'] = float(partial_data['summary']['ttt-other'])
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other'] = float(partial_data['summary']['timeloss-other'])
        results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected'] = float(partial_data['summary']['ttt-other-affected'])
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected'] = float(partial_data['summary']['timeloss-other-affected'])        

        results[location][i][alg_name][args_name][ev][seed]['ttt-other-var'] = float(partial_data['summary']['ttt-other-var'])
        results[location][i][alg_name][args_name][ev][seed]['ttt-other-std'] = float(partial_data['summary']['ttt-other-std'])

        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-var'] = float(partial_data['summary']['timeloss-other-var'])
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-std'] = float(partial_data['summary']['timeloss-other-std'])

        results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected-var'] = float(partial_data['summary']['ttt-other-affected-var'])
        results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected-std'] = float(partial_data['summary']['ttt-other-affected-std'])

        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected-var'] = float(partial_data['summary']['timeloss-other-affected-var'])
        results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected-std'] = float(partial_data['summary']['timeloss-other-affected-std'])

        results[location][i][alg_name][args_name][ev][seed]['ev-speed-avg'] = float(partial_data['summary']['ev-speed-avg'])

        results[location][i][alg_name][args_name][ev][seed]['other-speed-avg'] = float(partial_data['summary']['other-speed-avg'])
        results[location][i][alg_name][args_name][ev][seed]['other-speed-var'] = float(partial_data['summary']['other-speed-var'])
        results[location][i][alg_name][args_name][ev][seed]['other-speed-std'] = float(partial_data['summary']['other-speed-std'])

        results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-avg'] = float(partial_data['summary']['other-affected-speed-avg'])
        results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-var'] = float(partial_data['summary']['other-affected-speed-var'])
        results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-std'] = float(partial_data['summary']['other-affected-speed-std'])        

        when_enter = int(partial_data['summary']['when_enter'])
        when_left = int(partial_data['summary']['when_left'])

        results[location][i][alg_name][args_name][ev][seed]['n_vehicles'] = int(partial_data['summary']['n_vehicles'])
        results[location][i][alg_name][args_name][ev][seed]['avg_car_density'] = mean(partial_data[car_density][when_enter:when_left+1][1])

        results[location][i][alg_name][args_name][ev][seed]['ev_was_teleported'] = bool(partial_data['summary']['ev_was_teleported'])

        partial_data = None

        return results
      else:
        print('{} from {}-{} was ignored!'.format(f,location,i))
  else:
    print('{} not exists'.format(current_base_folder))