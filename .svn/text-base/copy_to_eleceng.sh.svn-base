cd doc
make clean html latexpdf
#make clean html 
cd ..

scp -r doc/build/html/* sknight@aaron:/home/www/personal/sknight/AutoNetkit/                   
scp doc/build/latex/AutoNetkit.pdf sknight@aaron:/home/www/personal/sknight/AutoNetkit/AutoNetkit.pdf




#python setup.py sdist bdist_egg
scp -r dist/* sknight@aaron:/home/www/personal/sknight/AutoNetkit/    
   


         
tar -czf examples/examples.tar.gz examples/*.py examples/topologies/*.gml
scp -r examples/examples.tar.gz sknight@aaron:/home/www/personal/sknight/AutoNetkit/examples.tar.gz   
scp -r examples/topologies/* sknight@aaron:/home/www/personal/sknight/AutoNetkit/topologies    
 
