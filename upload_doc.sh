cd doc/
make html latexpdf
cp build/latex/AutoNetkit.pdf build/html/_downloads/
cd ..
python setup.py upload_sphinx
