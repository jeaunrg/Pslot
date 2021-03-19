from src.candidates import Candidate
import pandas
import json
import random
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.patches as mpatches
import pdb
import copy
import os
from src.misc import vprint

class Bloc:
    """
    ex: Task Force, SSPI, ...
    """
    def __init__(self, name):
        self.name = name
        self.blocslots = []
    def addBlocslot(self, blocslot):
        self.blocslots.append(blocslot)
    def reset(self):
        for blocslot in self.blocslots:
            blocslot.reset()
class Slot:
    """
    ex: astreinte, demi-garde, ou garde
    """
    def __init__(self, name, blocs):
        self.name = name
        self.blocs = blocs

class Day:
    """
    ex: Samedi 1 Decembre 2019
    """
    def __init__(self, id, name, num, month, year, isHoliday, slots):
        self.id = id
        self.name = name
        self.num = num
        self.month = month
        self.year = year
        self.isHoliday = isHoliday
        self.slots = slots
        self.index = " ".join([name, str(num), month, year])
        self.dayslots = {}
        self.blocslots = []
        self.previous = None
        self.next = None
        self.computeDayslots()

    def computeDayslots(self):
        for slot in self.slots:
            dayslot = Dayslot(self, slot)
            self.dayslots[dayslot.slot.name] = dayslot
            self.blocslots += dayslot.blocslots


class Dayslot:
    """
    slot for a specific day
    ex: astreinte, le Samedi 1 Decembre 2019
    """
    def __init__(self, day, slot):
        self.day = day
        if isinstance(slot, Slot):
            self.slot = slot
            blocs = self.slot.blocs
        else:
            self.slot = slot[0]
            blocs = slot[1:]
        self.index = " - ".join([day.index, self.slot.name])
        self.blocslots = []
        for bloc in blocs:
            self.blocslots.append(Blocslots(self, bloc))


class Blocslots:
    """
    slot for a specific bloc, for a specific day
    ex: astreinte en SSPI/Bloc, le Samedi 1 Decembre 2019
    """
    def __init__(self, dayslot, bloc):
        self.dayslot = dayslot
        self.bloc = bloc
        self.index = " - ".join([dayslot.index, bloc.name])
        self.ncandidates = 0
        self.candidates = []
        self.final_candidate = None
        bloc.addBlocslot(self)
    def addCandidate(self, candidate):
        """
        add candidate to the list of potential candidates
        """
        if candidate not in self.candidates:
            self.candidates.append(candidate)
            self.ncandidates += 1
    def sortCandidates(self, randomize):
        """
        sort candidates based on their score (penality, wish_score, priority)
        """
        self.candidates = sorted(self.candidates, key=lambda c: c.getScore(self, randomize=randomize), reverse=True)
        return self.candidates
    def setFinalCandidate(self, candidate):
        """
        set final unique candidate for this bloc slot
        """
        self.final_candidate = candidate
        candidate.addFinalBlocslot(self)
    def reset(self):
        self.final_candidate = None

class Schedule:
    def __init__(self):
        self.blocs = {}
        self.slots = {}
        self.days = {}
        self.candidates = {}
        self.blocslots = []
        self.custom_conditions = ""
        self.dataframe = None

    # load parameters
    def loadInfos(self, path):
        with open(path) as f:
            data = json.load(f)
        self.addSlots(data['Creneaux'])
    def loadDays(self, path):
        with open(path) as f:
            data = json.load(f)
        self.addDays(data)
    def loadCandidates(self, path):
        with open(path) as f:
            data = json.load(f)
        self.addCandidates(data)

    # set parameters
    def addBlocs(self, bloc_names):
        blocs = []
        for bloc_name in bloc_names:
            bloc = Bloc(bloc_name)
            self.blocs[bloc_name] = bloc
            blocs.append(bloc)
        return blocs

    def addSlots(self, slot_params):
        slots = []
        for slot_name, bloc_names in slot_params.items():
            blocs = self.addBlocs(bloc_names)
            slot = Slot(slot_name, blocs)
            self.slots[slot_name] = slot
            slots.append(slot)
        return slots

    def addDays(self, day_params):
        prev_day_id = None
        for day_id, day_param in day_params.items():
            slots = []
            for sn in day_param["creneaux"]:
                if len(sn.split(':'))>1:
                    ns = sn.split(':')
                    slots.append([self.slots[ns[0]], *[self.blocs[n] for n in ns[1:]]])
                else:
                    slots.append(self.slots[sn])
            dayname = day_param["name"].split(" ")
            isHoliday = day_param["ferie"]
            day = Day(day_id, *dayname, isHoliday, slots)
            self.days[day_id] = day
            if prev_day_id is not None:
                day.previous = self.days[prev_day_id]
                self.days[prev_day_id].next = day
            prev_day_id = day_id

    def addCandidate(self, candidate_id, candidate_param):
        # @DC - ajout du test candidate_id=="END"
        if candidate_id.endswith("-XX") or candidate_id=="infos" or candidate_id=="END":
            return
        firstname, name, statut, priority = candidate_param["prenom"], candidate_param["nom"], candidate_param["statut"], candidate_param["priorite"]
        try:
            initiales = candidate_param["initiales"]
        except:
            initiales = 'UK'
        candidate = Candidate(candidate_id, firstname, name, initiales, statut, priority)
        self.candidates[candidate_id] = candidate
        candidate.schedule = self
        # set candidate parameters/desiderata
        candidate.giveAccessToBlocs(candidate_param["blocs"])
        candidate.setDesiderata(**candidate_param["desiderata"])
        for k, values in candidate_param["nombre"].items():
            candidate.setNumber(values["min"], values["max"], type=k)
        candidate.setConditions(candidate_param["conditions"])
        return candidate

    def addCandidates(self, candidate_params):
        for candidate_id, candidate_param in candidate_params.items():
            self.addCandidate(candidate_id, candidate_param)

    #-------------------------- process and fit functions ---------------------#
    def cand(self, candidate_id):
        """
        get candidate from its id
        """
        return self.candidates[candidate_id]

    def reset(self):
        """
        restore bloc and candidate initial parameters
        """
        for bloc in self.blocs.values():
            bloc.reset()
        for candidate in self.candidates.values():
            candidate.reset()

    def initBlocslots(self):
        """
        initialize schedule bloclot list
        """
        for day in self.days.values():
            for dayslot in day.dayslots.values():
                self.blocslots += dayslot.blocslots

    def buildDataframes(self):
        """
        build schedule dataframes after fitting
        """
        # get all uncomplete wishes
        uncomplete_wishes = {}
        for c in self.candidates.values():
            if not c.isObjectiveMet():
                for k, v in c.errors.items():
                    uncomplete_wishes[(c.name, k)] = v
        uncomplete_wishes = pd.DataFrame.from_dict(uncomplete_wishes).T

        # initialize schedule dataframe
        n_schedule_errors = 0
        colnames = ['id', 'day', 'daynum', 'month', 'year', 'slot', 'bloc', 'candidat id', 'statut', 'firstname', 'lastname', 'initiales']
        schedule = pandas.DataFrame(columns=colnames)
        for i, blocslot in enumerate(self.blocslots):
            # get blocslot final candidate
            candidate = blocslot.final_candidate
            if candidate is not None:
                cand_id, statut, firstname, lastname, initiales = candidate.id, candidate.statut, candidate.firstname, candidate.lastname, candidate.initiales
            else:
                cand_id, statut, firstname, lastname, initiales = '-', '-', '-', '-', '-'
                n_schedule_errors += 1
            # fill schedule dataframe
            schedule.loc[i, colnames] = [blocslot.dayslot.day.id, blocslot.dayslot.day.name,
                                         blocslot.dayslot.day.num, blocslot.dayslot.day.month,
                                         blocslot.dayslot.day.year, blocslot.dayslot.slot.name,
                                         blocslot.bloc.name, cand_id, statut, firstname, lastname,initiales]
        schedule = schedule.set_index(colnames[:-4])
        self.dataframe = copy.copy(schedule)
        return schedule, uncomplete_wishes, n_schedule_errors

    def checkFeasibility(self, verbose=False):
        """
        check if fitting can be performed perfectly (with no empty slots)
        by comparison of candidates demand and schedule supply
        """
        supply = {"total": 0, "DG": 0, "G": 0, "AT": 0}

        for blocslot in self.blocslots:
            supply['total'] += 1
            supply[blocslot.dayslot.slot.name] += 1
        if verbose:
            print("Bloc slots supply:", supply)

        min_diff = copy.copy(supply)
        max_diff = copy.copy(supply)
        min_demand = {"total": 0, "DG": 0, "G": 0, "AT": 0}
        max_demand = {"total": 0, "DG": 0, "G": 0, "AT": 0}
        for candidate in self.candidates.values():
            for k, (mini, maxi) in candidate.numbers.items():
                min_demand[k] += mini
                max_demand[k] += maxi
                min_diff[k] -= mini
                max_diff[k] -= maxi
        extra_demand = {k: -v for k, v in min_diff.items() if v<0}
        extra_supply = {k: v for k, v in max_diff.items() if v>0}
        if verbose:
            print("Bloc slots minimum demand:", min_demand)
            print("Bloc slots maximum demand:", max_demand)
        return extra_supply, extra_demand


    def fit(self, randomize_candidates=True, save=None, ntimes=1, sort_slots_by=[], ascending=[], ignore_max_count=False, ignore_resents=False):
        """
        fit n times candidates desiderata to schedule,
        with a random parameter for each fit and save results to csv file

        Args
        randomize_candidates: boolean: randomize candidate selection when scores are equal
        sort_slots_by: list of (tuple or str): sort blocslots in this order
        ignore_max_count:   boolean:    if no one can fill a slot, ignore the best candidate max count
        ignore_resents:   boolean:    if no one can fill a slot, ignore the best candidate resents
        """
        n = 0
        while n != ntimes:
            # create text files to follow progression through webpage
            filename = os.path.join(save, "stop.txt")
            if os.path.exists(filename):
                break
            filename = os.path.join(save, "adv.txt")
            fp = open(filename, "w")
            fp.write("{0}/{1}".format(n + 1, ntimes))
            fp.close()

            # initialize
            if len(self.blocslots) == 0:
                self.initBlocslots()
            self.reset()
            extra_supply, extra_demand = self.checkFeasibility()
            if len(extra_supply) > 0:
                print("There is more supply than demand\nextra supply: {0}".format(extra_supply))
            if len(extra_demand) > 0:
                print("There is more demand than supply\nextra demand: {0}".format(extra_demand))


            # define blocslots order from sort_slots_by
            if len(sort_slots_by) == 0:
                blocslots = self.blocslots
            else:
                df_blocslots = {}
                for bs in self.blocslots:
                    df_blocslots[bs] = {}
                    df_blocslots[bs]['random'] = random.random()
                    df_blocslots[bs]['n candidates'] = bs.ncandidates
                    df_blocslots[bs]['slot'] = bs.dayslot.slot.name
                    df_blocslots[bs]['day'] = int(bs.dayslot.day.num)
                    # on considere les vendredi et les lundi feries comme des jours de weekend
                    df_blocslots[bs]['weekend'] = bs.dayslot.day.isHoliday
                    if bs.dayslot.day.name=='Vendredi':
                        df_blocslots[bs]['weekend'] = 'oui'
                df_blocslots = pd.DataFrame.from_dict(df_blocslots).T

                sort_by = copy.copy(sort_slots_by)
                for i, by in enumerate(sort_slots_by):
                    byIsTuple = isinstance(by, tuple)
                    if len(ascending) < i+1:
                        ascending.append(not byIsTuple)
                    if byIsTuple:
                        col = " - ".join(by)
                        df_blocslots[col] = df_blocslots[by[0]] == by[1]
                        sort_by[i] = col
                df_blocslots = df_blocslots.sort_values(by=sort_by, ascending=ascending)
                blocslots = list(df_blocslots.index)

            # set candidate for each blocslot
            for blocslot in blocslots:
                candidates = blocslot.sortCandidates(randomize=randomize_candidates)

                vprint("\n"+blocslot.index)

                # get candidates for this blocslot, sorted on their score
                if len(candidates) == 0:
                    continue
                best_candidate = candidates[0]
                score = best_candidate.score[blocslot]
                if score['block']==0 or score['cond']==0\
                        or (not ignore_max_count and score['max']==0)\
                        or (not ignore_resents and score['wish']==-1):
                    continue

                # best candidate as final candidate
                vprint("\tset best candidate "+best_candidate.initiales)
                blocslot.setFinalCandidate(best_candidate)

            # save schedule csv files
            if save is not None:
                schedule, unc, nerr = self.buildDataframes()
                nerrors = "{0:03d}-{1:03d}".format(nerr, unc.shape[0])
                schedule.to_csv(os.path.join(save, "out", "{0}_{1:03d}_output.csv".format(nerrors, n+1)), sep='\t', decimal=",", encoding="utf-16")
                unc.to_csv(os.path.join(save, "out", "{0}_{1:03d}_errors.csv".format(nerrors, n+1)), sep='\t', decimal=",", encoding="utf-16")
            n += 1
        # send signal of process end
        filename = os.path.join(save, "adv.txt")
        fp = open(filename, "w")
        fp.write("end")
        fp.close()
