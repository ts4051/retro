dir=$1
for file in {0..50}
do
    echo "/storage/home/pde3/retro/scripts/reco_file.sh $dir $file" | qsub -A cyberlamp \
-l qos=cl_open \
-l nodes=1:ppn=1 \
-l pmem=12000mb \
-l walltime=24:00:00 \
-N r$dir.$file \
-o /gpfs/scratch/pde3/retro/log/$dir.$file.log \
-e /gpfs/scratch/pde3/retro/log/$dir.$file.err
done
