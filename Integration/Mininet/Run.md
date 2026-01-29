# 1. Check if your VM is running
multipass list

# 2. If VM is stopped, start it
multipass start mininet-vm

# 3. Transfer a file to VM
cd /Users/davidjayakumar/Desktop/FYP_Phase2_Network_Defender

then

multipass transfer ./Integration/Mininet/my_topo.py mininet-vm:/home/ubuntu/

# 4. SSH into VM
multipass shell mininet-vm

# 5. Run Mininet
sudo mn --custom ~/my_topo.py --topo mytopo

# 6. Test connectivity
 h1 ping h2 <!-- ping between two hosts -->
pingall <!-- ping all hosts -->
net <!-- show network -->
nodes <!-- show nodes -->
dump <!-- show all node details -->

# 7. exit mininet
exit

# 8. stop VM
multipass stop mininet-vm
