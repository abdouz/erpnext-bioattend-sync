from threading import Thread
from multiprocessing.pool import ThreadPool
from time import sleep, perf_counter

from zkbase import get_devices, check_device

start_time = perf_counter()
devices = get_devices('C:\\bio-att-sync\\bio_devices_ips.csv')

print("Checking (" + str(len(devices)) + ") Devices...")

pool = ThreadPool(processes=len(devices))

async_results = []

for dev in devices:
    async_results.append(pool.apply_async(check_device, (dev,)))

success = 0
failed = 0
for i, res in enumerate(async_results):
    dev_data = res.get()

    print("<"+str(i+1)+">", dev_data)
    if dev_data[0] == 'SUCCESS':
        success += 1
    else:
        failed += 1

print("<" + str(success) + "> Success and", "<" + str(failed) + "> Failed")

end_time = perf_counter()
print(f'It took {end_time- start_time: 0.2f} second(s) to complete.')