import sys
import redis
import asyncio
import math
from time import sleep, perf_counter
from frappeclientasync import FrappeClientAsync
import local_config as config
from redis_base import EmpDB

erp_url = getattr(config, 'erp_url')
api_key = getattr(config, 'api_key')
api_secret = getattr(config, 'api_secret')

checkins_per_request = getattr(config, 'checkins_per_request')
max_simult_requests = getattr(config, 'max_simult_requests')
max_iterations_per_task = getattr(config, 'max_iterations_per_task')


async def main():

    emp_fltrs = {"attendance_device_id": ("!=", ""), "status": ("=", "Active")}
    emp_flds = ['name', 'attendance_device_id', 'employee_name']
    emp_chk_flds = ['employee', 'time', 'log_type', 'device_id']
    start_time = perf_counter()

    emp_db = EmpDB()

    client = FrappeClientAsync(erp_url)
    client.authenticate(api_key, api_secret)

    # Get current checkins in ERPNext
    resp = await client.simult_bulk_get_list('Employee Checkin', fields=emp_chk_flds, limit_page_length=500)

    all_checkins = []
    for doc in resp:
        all_checkins += await doc

    # Compare with redis db, mark imported and insert new to redis DB
    emp_db.match_online_with_db(all_checkins)

    # Fetch new records from redis DB
    checkins_chunks = emp_db.get_new_checkins(per_chunk=checkins_per_request*max_simult_requests)

    # Push new records to ERPNext
    duplicate_msg = "frappe.exceptions.ValidationError: This employee already has a log with the same timestamp."
    rcnt = 0
    for i in range(0, max_iterations_per_task):
        resp = await client.simult_bulk_insert(checkins_chunks[i], checkins_per_request)
        for r in resp:
            tresp = await r.text()
            rcnt += 1
            if duplicate_msg in tresp:
                print(rcnt, r.status, "Duplicate Record(s)\r\n")
            else:
                if r.status == "200":
                    emp_db.match_online_with_db(checkins_chunks[i])
                print(rcnt, r.status, tresp, "\r\n")
    
    print("Total Requests Created: "+str(rcnt), ", Total Records Pushed: "+str(rcnt*checkins_per_request))

    await client.session.close()

    end_time = perf_counter()
    print('Time Elapsed: ', math.ceil(end_time-start_time), ' Seconds')

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
