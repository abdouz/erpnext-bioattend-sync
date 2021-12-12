import sys
import redis
import asyncio
import math
from datetime import date, datetime, timedelta
from time import sleep, perf_counter
from frappeclientasync import FrappeClientAsync
import local_config as config

erp_url = getattr(config, 'erp_url')
api_key = getattr(config, 'api_key')
api_secret = getattr(config, 'api_secret')


async def main():
    start_time = perf_counter()

    client = FrappeClientAsync(erp_url)
    client.authenticate(api_key, api_secret)

    # Get current shifts in ERPNext
    resp = await client.get_list('Shift Type', fields=['name', 'start_time', 'end_time', 'last_sync_of_checkin'], limit_page_length=500)
    all_shifts = await resp

    shifts_to_sync = []

    for shift in all_shifts:
        shifts_to_sync.append({
            'doctype': 'Shift Type',
            'docname': shift['name'],
            'last_sync_of_checkin': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'enable_auto_attendance': True,
            })

    #print(shifts_to_sync)

    resp = await client.bulk_update(shifts_to_sync)
    print(resp.status, await resp.json())

    await client.session.close()

    end_time = perf_counter()
    print('Time Elapsed: ', math.ceil(end_time-start_time), ' Seconds')

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
