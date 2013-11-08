import lariat_utils
import tspl_utils

def flatten(x):
  result = []
  for el in x:
    if hasattr(el, "__iter__") and not isinstance(el, basestring):
      result.extend(flatten(el))
    else:
      result.append(el)

  return result

def summary_text(ld,ts):
  text=''
  text+='Job ID: ' + str(ts.j.id) + ', '
  text+='User: '   + ts.owner + ', '
  text+='Job Name: ' + tspl_utils.string_shorten(ts.j.acct['name'],15) + ', '
  text+='Queue: ' + ts.queue + '\n'
  text+='Start Time: ' + ts.start_date + ', End Time: ' + ts.end_date + '\n'
  text+='Status: ' + ts.status + '\n'
  text+='Hosts: ' + str(ts.numhosts) + ', Threads: ' + str(ld.threads) + \
         ', Wayness: ' + str(ld.wayness) + '\n'

  cnt = 0
  try:
    runtimes=ld.get_runtimes(ts.j.acct['end_time'])
    for ibr in ld.ld[ld.id]:
      text += 'ibrun ' + str(cnt) + ':\n'
      text+='    Executable: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['exec'],
                                                   ld.user,60,16) + '\n'
      text+='    CWD: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['cwd'], 
                                                     ld.user,60,9) + '\n'
      text+='    Run time: ' + str(float(runtimes[cnt])/3600.) + '\n'
      if len(ibr['pkgT']) > 0:
        text+= '    Linked modules:\n'
      for pkg in ibr['pkgT']:
        text += '        ' + pkg + '\n'
      cnt+=1
  except Exception as e:
    pass
  
  return text
    
