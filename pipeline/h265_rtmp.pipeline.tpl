rtmpsrc location=rtmp://127.0.0.1/###APP###/###NAME### !
flvdemux name=demux 

demux.video ! identity name=v_delay signal-handoffs=TRUE ! h264parse ! nvv4l2decoder ! nvvidconv ! 
nvvidconv interpolation-method=5 !
nvv4l2h265enc control-rate=1 qp-range="28,50:0,38:0,50" iframeinterval=60 preset-level=4 maxperf-enable=true EnableTwopassCBR=true insert-sps-pps=true name=venc_bps ! 
h265parse config-interval=-1 ! queue max-size-time=10000000000 max-size-buffers=1000 max-size-bytes=41943040 ! mux. 

demux.audio ! aacparse ! avdec_aac ! identity name=a_delay signal-handoffs=TRUE ! volume volume=1.0 ! 
audioconvert ! voaacenc bitrate=128000 ! aacparse ! queue max-size-time=10000000000 max-size-buffers=1000 ! mux. 

mpegtsmux name=mux ! 
appsink name=appsink
