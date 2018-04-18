
export PATH=$PATH:/storage/home/pde3/.local/bin
export PATH=/storage/home/pde3/anaconda2/bin:$PATH
export LD_LIBRARY_PATH=/gpfs/group/dfc13/default/usr/local/cuda-8.0/lib64:/gpfs/group/dfc13/default/software/multinest/lib:$LD_LIBRARY_PATH
export PATH=/gpfs/group/dfc13/default/usr/local/cuda-8.0/bin:$PATH
dir=$1
file=$2
/storage/home/pde3/retro/scripts/reco.sh /gpfs/group/dfc13/default/sim/retro/14600/$dir.$file 0 /gpfs/scratch/pde3/retro/recos/2018.04.18.02/14600/$dir.$file
