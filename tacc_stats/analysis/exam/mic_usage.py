from exams import Test

# Compute host- and time-averaged MIC user fraction

# Single mic usage < 1
# Double mic usage < 2

class MIC_Usage(Test):
  k1 = ['mic']      
  k2 = ['user_sum']
  comp_operator = '>'
  
  def compute_metric(self):
    # Get mic stats aggregated over all hosts and mics
    self.metric = 0.0
    schema = self.ts.j.schemas['mic']
    stats,Nhosts,Ndevs = self.ts.j.aggregate_stats('mic')

    # Get index of relevant events
    us_index = schema['user_sum'].index
    jc_index = schema['jiffy_counter'].index
    th_index = schema['threads_core'].index
    nc_index = schema['num_cores'].index

    # Compute user fraction over run
    # Assume threads*cores is constant in time
    self.metric = Nhosts * (stats[-1, us_index] - stats[0, us_index])*float( (stats[-1, jc_index]-stats[0, jc_index]) * stats[0, th_index] * stats[0, nc_index] )**-1
    return

