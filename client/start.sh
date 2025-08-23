#!/bin/bash
#source ~/miniconda3/etc/profile.d/conda.sh

# Run first script in env_one
nohup bash -c 'conda activate flask-audio && python audio_client_rasp.py' > audio_client.log 2>&1 &
