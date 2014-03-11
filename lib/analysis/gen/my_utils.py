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

def summary_text(ld,ts,maxwidth=55,max_ibrun_lines=45):
  text=''
  cnt = 0
  try:
    runtimes=ld.get_runtimes(ts.j.acct['end_time'])
    for ibr in ld.ld[ld.id]:
      text += 'ibrun ' + str(cnt) + ':\n'
      text+='    Executable: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['exec'],
                                                   ld.user,maxwidth,16) + '\n'
      text+='    CWD: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['cwd'], 
                                                     ld.user,maxwidth,9) + '\n'
      text+='    Run time: ' + str(float(runtimes[cnt])/3600.) + '\n'
      if len(ibr['pkgT']) > 0:
        text+= '    Linked modules:\n'
      for pkg in ibr['pkgT']:
        text += '        ' + pkg + '\n'
      cnt+=1
  except Exception as e:
    pass

  res=text.split('\n')
  if len(res) > max_ibrun_lines:
    text='...\n'+'\n'.join(res[-max_ibrun_lines:])


  top_text ='Job ID: ' + str(ts.j.id) + ', '
  top_text+='User: '   + ts.owner + ', '
  top_text+='Job Name: ' + tspl_utils.string_shorten(ts.j.acct['name'],15) + \
             ', '
  top_text+='Queue: ' + ts.queue + '\n'
  top_text+='Start Time: ' + ts.start_date + ', End Time: ' + ts.end_date + '\n'
  top_text+='Status: ' + ts.status + '\n'
  top_text+='Hosts: ' + str(ts.numhosts) + ', Threads: ' + str(ld.threads) + \
             ', Wayness: ' + str(ld.wayness) + '\n'

  text=top_text+text
  
  return text
    
