#!/bin/bash
cd /home/yashyv357/sketch-spark-engine
git pull origin main
chmod +x run_cron.sh
(crontab -l 2>/dev/null | grep -v run_cron.sh; echo "0 9 * * * /home/yashyv357/sketch-spark-engine/run_cron.sh") | crontab -
echo "Cron installed successfully!"
crontab -l
