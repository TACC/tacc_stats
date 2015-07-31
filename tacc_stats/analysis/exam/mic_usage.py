from exams import Test

class MIC_Usage(Test):
  k1 = ['mic']      
  k2 = ['user_sum']
  comp_operator = '>'
  
  def compute_metric(self):

    total = 0.0
    user_total = 0.0
    self.metric = 0.0
    for hostn,host in self.ts.j.hosts.iteritems():
      user = host.get_stats('mic','0','user_sum')[0:-1]
      jiffy = host.get_stats('mic','0','jiffy_counter')[0:-1]

      if len(jiffy) < 2: return
      total += jiffy[-1] - jiffy[0]
      user_total += user[-1] - user[0]
    
    metric = user_total/float(244*total)
    if metric < 1:
      self.metric = metric
      print self.metric
    return
