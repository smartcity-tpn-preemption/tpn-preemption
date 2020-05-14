import collections
import itertools
import multiprocessing

from functools import partial
from multiprocessing.dummy import Pool
from subprocess import call
import sys
import optparse
import json

def get_options():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option("--configfile", dest="configfile", 
                        help="Instance and algorithms parameters", metavar="FILE")
  opt_parser.add_option("--machine", dest="machine", 
                        help="Machine option in file", type="string")
  opt_parser.add_option("--basefolder", dest="basefolder", 
                        help="Base folder of scenarios", metavar="FILE")                                                   
  (options, args) = opt_parser.parse_args()
  return options

# this is the main entry point of this script
if __name__ == "__main__":
  options = get_options()

  if not options.configfile:
    sys.exit("Error: You must specify the Config File using the '--configfile' option")

  if not options.basefolder:
    sys.exit("Error: You must specify the Base Folder of scenarios using the '--basefolder' option")

  if not options.machine:
    sys.exit("Error: You must specify the Machine using '--machine' option")


  configfile = open(options.configfile,'r')
  config_values = json.loads(configfile.read(), object_pairs_hook=collections.OrderedDict)
  configfile.close()

  print(configfile)

  if options.machine not in config_values['machines']:
    sys.exit("Error: {} is not specifiend in {} file".format(options.machine,options.configfile))

  algorithms = config_values['algorithms']

  base_folder = options.basefolder
  locations = config_values['locations']
  route_options = config_values['prefix']
  number_of_instances = config_values['scenarios']
  seeds = config_values['machines'][options.machine]['seeds']
  tasks = config_values['machines'][options.machine]['tasks']

  if 'threadnum' in config_values['machines'][options.machine]:
    threadnum = config_values['machines'][options.machine]['threadnum']
  else:
    threadnum = multiprocessing.cpu_count()

  commands = []

  for route_option in route_options:
    for location in locations:
      evs = locations[location]['evs']
      for i in number_of_instances:
        current_base_folder = base_folder + '/' + location + '/' + location + '-' + str(i)

        for ev in evs:
          for j in seeds:
            command = 'python3 new_proposal.py --scenario '+current_base_folder+' --nogui --ev '+ev+' --sm '+str(j)+' --prefix '+route_option

            for alg, args in algorithms.items():
              algcommand = command + ' --alg '+alg+' '

              if len(args) == 0:
                commands.append(algcommand)
              else:
                partial_commands = []
                for parameter, values in args.items():
                  partial_parameters = []
                  for p in values:
                    partial_parameters.append(' --'+parameter+' '+str(p)+' ')
                  partial_commands.append(partial_parameters)
                
                if len(partial_commands) == 1:
                  for element in itertools.product(partial_commands[0]):
                    final_args = ''
                    for w in element:
                      final_args = final_args + ' ' + w + ' '   
                    commands.append(algcommand+' '+final_args)
                elif len(partial_commands) == 2:
                  for element in itertools.product(partial_commands[0],partial_commands[1]):
                    final_args = ''
                    for w in element:
                      final_args = final_args + ' ' + w + ' '   
                    commands.append(algcommand+' '+final_args)
                elif len(partial_commands) == 3:
                  for element in itertools.product(partial_commands[0],partial_commands[1],partial_commands[2]):
                    final_args = ''
                    for w in element:
                      final_args = final_args + ' ' + w + ' ' 
                    commands.append(algcommand+' '+final_args)
                elif len(partial_commands) == 4:
                  for element in itertools.product(partial_commands[0],partial_commands[1],partial_commands[2],partial_commands[3]):
                    final_args = ''
                    for w in element:
                      final_args = final_args + ' ' + w + ' ' 
                    commands.append(algcommand+' '+final_args)

  failed_commands = {}
  pool = Pool(threadnum*tasks) # using the number of cores to run concurrent commands at same time
  for i, returncode in enumerate(pool.imap(partial(call, shell=True), commands)):
    if returncode != 0:
      failed_commands[i] = returncode
    else:
      print("%d command has successfuly finished" % i )

  for i in failed_commands:
    print("%d command failed with statuscode=%d (%s)" % (i,failed_commands[i],commands[i]) )

