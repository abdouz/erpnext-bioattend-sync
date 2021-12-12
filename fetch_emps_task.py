import redis
import asyncio
from frappeclientasync import FrappeClientAsync
import local_config as config
from redis_base import EmpDB

erp_url = getattr(config, 'erp_url')
api_key = getattr(config, 'api_key')
api_secret = getattr(config, 'api_secret')

emp_fltrs = {"attendance_device_id": ("!=", ""), "status": ("=", "Active")}
emp_flds = ['name', 'attendance_device_id', 'employee_name']

emp_db = EmpDB()

async def main():
    client = FrappeClientAsync(erp_url)
    client.authenticate(api_key, api_secret)

    resp = await client.simult_bulk_get_list('Employee', fields=emp_flds, filters=emp_fltrs, limit_page_length=300)

    all_emps = []
    for doc in resp:
        all_emps += await doc

    emp_db.insert_emps(all_emps)

    await client.session.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
