import pdb
import random
import sys
import os
from src.candidates import Candidate
from src.misc import generateDays, generateCandidates
from src.scheduling import Schedule

if __name__ == "__main__":
    mainpath = os.path.dirname(os.path.realpath(__file__))
    datapath = os.path.join(mainpath, "data")
    force = 0
    n = 10
    argc = len(sys.argv)
    for i in range(argc):
        if sys.argv[i] == '-force':
            force = 1
        if sys.argv[i] == '-d' and i < argc - 1:
            datapath = sys.argv[i + 1];
            i += 1
        if sys.argv[i] == '-n' and i < argc - 1:
            n = sys.argv[i + 1];
            i += 1

    if force == 1:
        days = generateDays(start=0, ndays=30, save=os.path.join(datapath, "jours.json"))
        generateCandidates(days, save=os.path.join(datapath, "candidates.json"))
    print(datapath)

    schedule = Schedule()
    schedule.loadInfos(os.path.join(datapath, "infos.json"))
    schedule.loadDays(os.path.join(datapath, "jours.json"))
    schedule.loadCandidates(os.path.join(datapath, "candidates.json"))

    # fit schedule
    print(n)
    sort_slots_by = [("weekend", 'oui'), ("slot","AT"),  ("slot", "G"),("slot", "DG"), "n candidates", "random"]
    # sort_slots_by = ['day', ("slot", "G"), ("slot", "DG"), ("slot","AT")]
    schedule.fit(save=datapath, ntimes=int(n), randomize_candidates=True,
                 sort_slots_by=sort_slots_by, ignore_max_count=False, ignore_resents=False)
