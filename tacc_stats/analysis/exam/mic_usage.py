from exams import Test

class MICUsage(Test):
  k1 = ['ib_sw', 'net']      
  k2 = ['scif0/1','mic0' ]
  comp_operator = '>'
  aggregate = False
  
  def compute_metric(self):
    data = {}
    data1 = 0
    for hostn,host in self.ts.j.hosts.iteritems():
      data[hostn] = host.get_stats('net','mic0','rx_bytes')#+host.get_stats('net','mic0','tx_bytes')]
      if len(data[hostn]) > 2:
        data1 += data[hostn][-2]-data[hostn][0]

    if data1 > 1000: print self.ts.j.acct,data1

    self.metric = data1#self.arc(data)

    
    return
