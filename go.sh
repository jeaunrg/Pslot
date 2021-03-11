#!/bin/bash

FOLDER=$1
if [ "$FOLDER" = "" ] || [ ! -d $FOLDER ]
then
	echo folder does not exist
	exit
fi
N=$2
if [ "$N" == "" ]
then
	N=10
fi

source /home/apache/.bashrc

rm -rf $FOLDER/data/out
rm -f $FOLDER/data/adv.txt $FOLDER/data/stop.txt
mkdir $FOLDER/data/out
cd $FOLDER/data
for F in candidates.json conditions.txt infos.json jours.json
do
	/home/apache/bin/rconv $F
done
python /home/apache/PSLOT/main.py -d $FOLDER/data -n $N

