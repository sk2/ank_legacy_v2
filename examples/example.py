import sys                 
sys.path.append('../')

from AutoNetkit.internet import Internet
                                  
inet = Internet("topologies/aarnet.yaml")    
  
inet.add_dns()   

inet.compile()  

inet.plot()      

inet.deploy(host = "netkithost", username = "autonetkit")         


