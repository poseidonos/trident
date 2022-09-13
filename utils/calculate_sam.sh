pwd
rm -fr ../sam_cli.cfg
cp sam_cli.cfg ../
sed -i "s|pospath|$(pwd)|" ../sam_cli.cfg
