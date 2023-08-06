#!/bin/bash
while true; do
        now=$(date +%s)
        now=${now%.*}
        restart_date=$(date -d "tomorrow 05:00" +%s)
        restart_date=${restart_date%.*}
        echo $restart_date | gawk '{print strftime("%c", $0)}'
        sleep_time=$(($restart_date-$now))
	echo $sleep_time
        timeout $sleep_time python3 asyncbot.py
done
