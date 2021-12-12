import math
from time import sleep, perf_counter

import local_config as config
from redis_base import EmpDB
from zk_base import AttendDevices

devices_csv = getattr(config, 'devices_csv')

emp_db = EmpDB()
devs = AttendDevices(devices_csv)

all_emps = emp_db.get_all_emps()

start_time = perf_counter()

all_check_ins = devs.fetch_checkins(all_emps, emp_db.insert_checkin)

print(len(all_check_ins))

end_time = perf_counter()
print('Time Elapsed: ', math.ceil(end_time-start_time), ' Seconds')

