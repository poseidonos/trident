if [ $# != 1 ]; then
	echo 'USAGE :tag'
	exit
fi

export GIT_SSL_NO_VERIFY=1
echo `date +%Y-%m-%d` `date +%H:%M:%S`
mkdir -p /root/poseidon
cd /root/poseidon
echo Remove ibofos directory
rm -rf ibofos
git clone https://git.memswdev.samsungds.net:7990/scm/ibof/ibofos.git
cd ibofos
git checkout $1
cd script
./pkgdep.sh | tee pkgdep.log
cd ../lib/spdk/scripts
./pkgdep.sh | tee pkgdep.log
cd /root/poseidon/pos/lib
./build_lib_internal.sh | tee build_lib_internal.log
cd ../script
./build_ibofos.sh -i | tee build_ibofos.log
cd script
./setup_env.sh
