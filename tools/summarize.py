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

def get_options():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option("--method", type="string", dest="method", default="append")                   
  opt_parser.add_option("--basefolder", type="string", dest="basefolder", default="../docker-sumo-interscity-spres-ev-scenarios")
  opt_parser.add_option("--location", type="string", dest="location", default="sp")
  opt_parser.add_option("--instance", type="string", dest="instance", default="1")
  opt_parser.add_option("--jsonfile", type="string", dest="jsonfile")
  opt_parser.add_option("--outputfile", dest="outputfile", 
                        help="Output File", metavar="FILE")
  opt_parser.add_option("--prefix", type="string", dest="prefix")
  (options, args) = opt_parser.parse_args()
  return options

# this is the main entry point of this script
if __name__ == "__main__":

  options = get_options()

  print(options)

  if not options.outputfile:
    sys.exit("Error: You must specify the Output file using the '--outputfile' option")  

  if not options.jsonfile:
    sys.exit("Error: You must specify the JSON file using the '--jsonfile' option")

  if not options.prefix:
    sys.exit("Error: You must specify the prefix using the '--prefix' option")   


  results = {}

  if (options.method == 'read' or options.method == 'append') and os.path.isfile(options.outputfile):
    file_tmp = open(options.outputfile,'r')
    results = json.loads(file_tmp.read())
    file_tmp.close()    


  if not os.path.isfile(options.outputfile) or options.method == 'append' or options.method == 'override':
    location = options.location
    if options.method == 'override' or location not in results:
      results[location] = {}

    i = options.instance
    current_base_folder = options.basefolder + '/' + location + '/' + location + '-' + str(i) + '/results/' + options.prefix

    if options.method == 'override' or i not in results[location]:
      results[location][i] = {}

    if os.path.exists(current_base_folder):
      f = options.jsonfile
      name_parts = f.split('.json')[0].split('_')
      sheet_summary = f.split('.json')[0]
      car_density = 'Car density'

      alg_name = name_parts[0].split('!')[1]
      ev = name_parts[1].split('!')[1]
      seed = name_parts[2].split('!')[1]

      if options.method == 'override' or alg_name not in results[location][i]:
        results[location][i][alg_name] = {}
      
      args_name = '_'.join(name_parts[3:len(name_parts)])

      if options.method == 'override' or args_name not in results[location][i][alg_name]:
        results[location][i][alg_name][args_name] = {}

      if options.method == 'override' or ev not in results[location][i][alg_name][args_name]:
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

      if options.method == 'override' or (options.method == 'append' and was_empty):
        print('processing '+f+' from '+location + '-' + str(i)+'...')
        #partial_data = get_data(current_base_folder+'/'+f)        
        file_tmp = open(current_base_folder+'/'+f,'r')
        partial_data = json.loads(file_tmp.read())
        file_tmp.close()   

        # results[location][i][alg_name][args_name][ev][seed]['ttt-ev'] = float(partial_data[sheet_summary][4][1])
        # results[location][i][alg_name][args_name][ev][seed]['timeloss-ev'] = float(partial_data[sheet_summary][4][2])
        # results[location][i][alg_name][args_name][ev][seed]['ttt-other'] = float(partial_data[sheet_summary][5][1])
        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other'] = float(partial_data[sheet_summary][5][2])
        # results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected'] = float(partial_data[sheet_summary][8][1])
        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected'] = float(partial_data[sheet_summary][8][2])        

        # results[location][i][alg_name][args_name][ev][seed]['ttt-other-var'] = float(partial_data[sheet_summary][6][1])
        # results[location][i][alg_name][args_name][ev][seed]['ttt-other-std'] = float(partial_data[sheet_summary][7][1])

        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other-var'] = float(partial_data[sheet_summary][6][2])
        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other-std'] = float(partial_data[sheet_summary][7][2])

        # results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected-var'] = float(partial_data[sheet_summary][9][1])
        # results[location][i][alg_name][args_name][ev][seed]['ttt-other-affected-std'] = float(partial_data[sheet_summary][10][1])

        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected-var'] = float(partial_data[sheet_summary][9][2])
        # results[location][i][alg_name][args_name][ev][seed]['timeloss-other-affected-std'] = float(partial_data[sheet_summary][10][2])

        # results[location][i][alg_name][args_name][ev][seed]['ev-speed-avg'] = float(partial_data[sheet_summary][12][1])

        # results[location][i][alg_name][args_name][ev][seed]['other-speed-avg'] = float(partial_data[sheet_summary][14][1])
        # results[location][i][alg_name][args_name][ev][seed]['other-speed-var'] = float(partial_data[sheet_summary][15][1])
        # results[location][i][alg_name][args_name][ev][seed]['other-speed-std'] = float(partial_data[sheet_summary][16][1])

        # results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-avg'] = float(partial_data[sheet_summary][18][1])
        # results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-var'] = float(partial_data[sheet_summary][19][1])
        # results[location][i][alg_name][args_name][ev][seed]['other-affected-speed-std'] = float(partial_data[sheet_summary][20][1])        

        # when_enter = int(partial_data[sheet_summary][1][3])
        # when_left = int(partial_data[sheet_summary][1][4])

        # results[location][i][alg_name][args_name][ev][seed]['n_vehicles'] = int(partial_data[sheet_summary][1][2])
        # results[location][i][alg_name][args_name][ev][seed]['avg_car_density'] = mean(partial_data[car_density][when_enter:when_left+1][1])

        # results[location][i][alg_name][args_name][ev][seed]['ev_was_teleported'] = bool(partial_data[sheet_summary][1][9])





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
      else:
        print(f+' from '+location + '-' + str(i)+' was ignored!')
  else:
    print(current_base_folder+' not exists')

  file_tmp = open(options.outputfile,'w+')
  file_tmp.write(json.dumps(results))
  file_tmp.close()


#  file_tmp = open(options.outputfile,'r')
#  results = json.loads(file_tmp.read())
#  file_tmp.close()
  
  #location_to_check = 'sp'
  #alg_to_check = 'rfid'
  #args_to_check = 'dd!50.0nc!1'
  #data_to_plot = []
  #xticks = []
  #xticks_n = []
  #x = 1
  #for i in number_of_instances:
  #  data_from_scenario = []
  #  xtick = None
  #  for seed in results[location_to_check][i][alg_to_check][args_to_check]:
  #    result_after = results[location_to_check][i][alg_to_check][args_to_check][ev][seed]['ttt-ev']
  #    result_before = results[location_to_check][i]['no-preemption'][''][ev][seed]['ttt-ev']
  #    result = (1-(result_after/result_before))*100
  #    print(i+' seed:'+str(seed)+' rb:'+str(result_before)+' ra:'+str(result_after)+' r:'+str(result))
  #    data_from_scenario.append(result)
  #    xtick = results[location_to_check][i][alg_to_check][args_to_check][ev][seed]['n_vehicles']
  #  xticks_n.append(x)
  #  x += 1
  #  data_to_plot.append(data_from_scenario)
  #  xticks.append(xtick)


  #print(data_to_plot)

  #plt.boxplot(data_to_plot)
  #plt.title('Boxplot - rfid-dd!50.0nc!1')
  #plt.xlabel('Nº of vehicles')
  #plt.ylabel('(1-(ttt_after/ttt_before)*)100')
  #plt.savefig('./rfid-dd!50.0nc!1.png', dpi=300)
  #plt.xticks(xticks_n, xticks)
  #plt.show()
    
  #print('Done!')
  #sys.exit(0)
