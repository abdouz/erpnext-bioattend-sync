#!/bin/bash

python ./fetch_emps_task.py
python ./fetch_attends_task.py
python ./push_checkins_task.py
sleep 3m
python ./update_shifts_task.py
