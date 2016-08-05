:: Generates the documentation. Make sure to have Sphinx installed. I use 3.3+ package style with no __init__.py which Sphinx doesn't like, I have a modified sphinx-apidoc which I can give you if Sphinx still hasn't fixed this.

sphinx-apidoc -e -F -o documentation -H luserver -A lcdr -V prototype -R prototype luserver
cd documentation
make html
cd ..