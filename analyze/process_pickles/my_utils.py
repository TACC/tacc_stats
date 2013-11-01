import lariat_utils

def flatten(x):
  result = []
  for el in x:
    if hasattr(el, "__iter__") and not isinstance(el, basestring):
      result.extend(flatten(el))
    else:
      result.append(el)

  return result

def text(ld,ts):
  text=''
  text+='Job ID: ' + str(ld.id) + '\n'
  text+='User: '   + ld.user + '\n'
  text+='Start Time: ' + ts.start_date + ', End Time: ' + ts.end_date + '\n'
  text+='Hosts: ' + str(ts.numhosts) + ', Threads: ' + str(ld.threads) + \
         ', Wayness: ' + str(ld.wayness) + '\n'

  cnt = 0
  try:
    for ibr in ld.ld[ld.id]:
      text += 'ibrun ' + str(cnt) + ':\n'
      text+='    Executable: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['exec'],
                                                   ld.user,50,16) + '\n'
      text+='    CWD: ' + \
             lariat_utils.replace_and_wrap_path_bits(ibr['cwd'], 
                                                     ld.user,50,9) + '\n'
      if len(ibr['pkgT']) > 0:
        text+= '    Linked modules:\n'
      for pkg in ibr['pkgT']:
        text += '        ' + pkg + '\n'
      cnt+=1
  except:
    pass

  return text
    
