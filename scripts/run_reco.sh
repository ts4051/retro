#for file in {0..41}
#do
file=20
for evt in {0..30}
do
./reco.sh /data/icecube/sim/ic86/retro/14600/0.$file $evt /data/peller/retro/recos/2018.04.17/14600/0.$file
done
#done
#evt=1
#./reco.sh /data/icecube/sim/ic86/retro/14600/13.$file $evt /data/peller/retro/recos/2018.04.10/14600/13.$file
