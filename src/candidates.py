import random
import pdb
import copy
import numpy as np
from src.misc import vprint


class Candidate:
    def __init__(self, id, firstname, lastname, initiales, statut, priority=1):
        self.id = id
        self.firstname = firstname
        self.lastname = lastname
        self.initiales = initiales
        self.name = " ".join([firstname, lastname])
        self.statut = statut
        self.priority_score = priority

        self.schedule = None
        self.blocslots, self.final_blocslots = [], []
        self.wishes, self.resents = [], []
        self.numbers = {'total': [0, 10000]}
        self.conditions = {}
        self.errors = {}

        self.count = {}
        self.score = {}


    def setConditions(self, conditions):
        self.conditions = conditions

    def addFinalBlocslot(self, blocslot):
        self.final_blocslots.append(blocslot)
        self.checkConditions(blocslot)

    def reset(self):
        self.final_blocslots = []
        for blocslot in self.blocslots:
            self.initScore(blocslot)

    def setDesiderata(self, wishes=[], resents=[]):
        try:
            self.wishes = [self.schedule.days[w1].dayslots[w2] for w1, w2 in wishes if w2 in self.schedule.days[w1].dayslots.keys()]
            self.resents = [self.schedule.days[r1].dayslots[r2] for r1, r2 in resents if r2 in self.schedule.days[r1].dayslots.keys()]
        except KeyError as e:
            raise ValueError("{0} desiderata are wrong".format(self.name))

    def setNumber(self, nmin=None, nmax=None, type='total'):
        if nmin is None:
            nmin = 0
        if nmax is None:
            nmax = 10000
        self.numbers[type] = [nmin, nmax]

    def addBlocslot(self, blocslot):
        self.blocslots.append(blocslot)
        self.initScore(blocslot)

    def initScore(self, blocslot):
        wish = 0
        if blocslot.dayslot in self.wishes:
            wish = 1
        elif blocslot.dayslot in self.resents:
            wish = -1
        self.score[blocslot] = {'block': 1, 'force': 0, 'cond': 1, 'min': 1, 'max': 1, 'wish': wish}

    def giveAccessToBlocs(self, bloc_names):
        for bloc_name in bloc_names:
            bloc = self.schedule.blocs[bloc_name]
            for blocslot in bloc.blocslots:
                if blocslot not in self.blocslots:
                    self.addBlocslot(blocslot)
                blocslot.addCandidate(self)


    def getScore(self, blocslot, randomize=False):
        """
        score =
        block:    defaut 1, 0 si le candidat est deja sur un creneau au meme moment
        force:    defaut 0, 1 en cas de force majeure
        cond:     defaut 1, 0 si ça ne respecte pas les conditions
        max:      defaut 1, 0 si on atteint le compte max pour le creneaux
        min:      defaut 1, 0 si on atteint le compte min pour le creneaux
        wish:     defaut 0, -1 si le slot est dans les 'rejets', 1 si dans les souhaits
        priority: defaut 0, > 1 si on veut prioriser le candidat sur les autres
        random:   flottant entre 0 et 1, permet de randomiser l'output
                  lorsque 2 candidats ont les mêmes scores pour un bloc-slot donné.
        """
        score = [self.score[blocslot][i] for i in ['block', 'force', 'cond', 'max', 'min', 'wish']]
        score.append(self.priority_score)
        if randomize:
            score.append(random.random())
        return score

    def reachMax(self, slot_name='total'):
        vprint('\t\treach ' +slot_name+ ' max')
        for blocslot in self.blocslots:
            if slot_name == 'total' or blocslot.dayslot.slot.name == slot_name:
                if blocslot not in self.final_blocslots and self.score[blocslot]['max'] != 0:
                    self.score[blocslot]['max'] = 0

    def reachMin(self, slot_name='total'):
        vprint('\t\treach ' +slot_name+ ' min')
        for blocslot in self.blocslots:
            if slot_name == 'total' or blocslot.dayslot.slot.name == slot_name:
                if blocslot not in self.final_blocslots and self.score[blocslot]['min'] != 0:
                    self.score[blocslot]['min'] = 0

    def block(self, blocslots):
        for blocslot in blocslots:
            if blocslot.final_candidate != self and blocslot in self.blocslots:
                vprint('\t\t', 'block', blocslot.index)
                self.score[blocslot]['block'] = 0

    def force(self, blocslots):
        for blocslot in blocslots:
            if blocslot.final_candidate != self and blocslot in self.blocslots:
                vprint('\t\t', 'force', blocslot.index)
                self.score[blocslot]['force'] = 1

    def disable(self, blocslots):
        for blocslot in blocslots:
            if blocslot.final_candidate != self and blocslot in self.blocslots:
                vprint('\t\t', 'disable', blocslot.index)
                self.score[blocslot]['cond'] = 0

    def updateCount(self):
        self.count = {k: 0 for k in self.numbers.keys()}
        self.count['total'] = len(self.final_blocslots)
        for blocslot in self.final_blocslots:
            if blocslot.dayslot.slot.name not in self.count.keys():
                self.count[blocslot.dayslot.slot.name] = 1
            else:
                self.count[blocslot.dayslot.slot.name] += 1

    def checkCountExceed(self):
        self.updateCount()
        nmin, nmax = self.numbers['total']
        if self.count['total'] == nmax:
            self.reachMax()
        else:
            if self.count['total'] == nmin:
                self.reachMin()
            for slot_name, (nmin, nmax) in self.numbers.items():
                if self.count[slot_name] == nmax:
                    self.reachMax(slot_name)
                elif self.count[slot_name] == nmin:
                    self.reachMin(slot_name)

    def isObjectiveMet(self):
        for k, count in self.count.items():
            if count < self.numbers[k][0]:
                self.errors[k] = {'min. asked': self.numbers[k][0], 'given': count}
        return len(self.errors) == 0


    def getCondition(self, name):
        if name not in self.conditions.keys():
            self.conditions[name] = False
        if self.conditions[name]:
            vprint("\t"+name)
        return self.conditions[name]

    def checkConditions(self, blocslot):
        self.checkCountExceed()
        day = blocslot.dayslot.day
        slot = blocslot.dayslot.slot
        bloc = blocslot.bloc
        working_days = [bs.dayslot.day for bs in self.final_blocslots]

        def getBlocslots(delta=0, slotname=None):
            d = getDay(delta)
            if d is None:
                return []
            if slotname is None:
                return d.blocslots
            elif slotname in d.dayslots.keys():
                return d.dayslots[slotname].blocslots
            else:
                return []

        def getDay(delta=1):
            d = copy.copy(day)
            for _ in range(np.abs(delta)):
                if delta < 0:
                    d = d.previous
                else:
                    d = d.next
                if d is None:
                    return
            return d


        #----------------------- contraintes obligatoires----------------------#
        # si on fait une DG/AT/G un jour, on ne peut pas etre sur un autre creneau de DG/AT/G au meme moment
        # a moins de savoir se teleporter
        if slot.name == 'AT':
            self.block(getBlocslots(0, 'AT'))
        elif slot.name == 'DG':
            self.block(getBlocslots(0, 'DG'))
        elif slot.name == 'G':
            self.block(getBlocslots(0, 'G'))

        #----------------------- contraintes d'exclusion ----------------------#
        # on ne peut pas etre de demi-garde et de garde le meme jour
        if self.getCondition('cond0'):
            if slot.name == "DG":
                self.disable(getBlocslots(0, "G"))
            elif slot.name == "G":
                self.disable(getBlocslots(0, "DG"))

        # on ne peut pas enchainer 3 jours de gardes/demi-gardes d'affile
        if self.getCondition('cond1'):
            if slot.name in ['DG', 'G']:
                if getDay(1) in working_days:
                    self.disable(getBlocslots(2))
                    self.disable(getBlocslots(-1))
                elif getDay(2) in working_days:
                    self.disable(getBlocslots(1))
                elif getDay(-1) in working_days:
                    self.disable(getBlocslots(1))
                    self.disable(getBlocslots(-2))
                elif getDay(-2) in working_days:
                    self.disable(getBlocslots(-1))

        # si on est de garde une nuit on ne peut pas faire de demi-garde le lendemain
        if self.getCondition('cond2'):
            if slot.name == 'G':
                self.disable(getBlocslots(1, 'DG'))
            elif slot.name == 'DG':
                self.disable(getBlocslots(-1, 'G'))

        # si on est de garde une nuit on ne peut pas faire d'astreinte le lendemain
        if self.getCondition('cond3'):
            if slot.name == 'G':
                self.disable(getBlocslots(1, 'AT'))
            elif slot.name == 'AT':
                self.disable(getBlocslots(-1, 'G'))

        # si on est de demi-garde on ne peut pas etre de garde le lendemain
        # sinon on est fatigue
        if self.getCondition('cond4'):
            if slot.name == "DG":
                self.disable(getBlocslots(1, "G"))
            elif slot.name == "G":
                self.disable(getBlocslots(-1, "DG"))

        # si on est d'astreinte un weekend on ne peut pas l'etre le weekend d'apres
        # (prend en compte les weekend prolonges)
        if self.getCondition('cond6'):
            # weekend
            if day.name == 'Samedi' and slot.name == 'AT':
                for i in [-8, -7, -6, -5, 6, 7, 8, 9]: #
                    self.disable(getBlocslots(i, 'AT'))
            elif day.name == 'Dimanche' and slot.name == 'AT':
                for i in [-9, -8, -7, -6, 5, 6, 7, 8]: #
                    self.disable(getBlocslots(i, 'AT'))
            # et jours feries...
            elif day.name == 'Vendredi' and slot.name == 'AT':
                for i in [-7, -6, -5, -4, 7, 8, 9, 10]: #
                    self.disable(getBlocslots(i, 'AT'))
            elif day.name == 'Lundi' and slot.name == 'AT':
                for i in [-10, -9, -8, -7, 4, 5, 6, 7]: #
                    self.disable(getBlocslots(i, 'AT'))


        #----------------------- contraintes d'inclusion  ---------------------#
        # si on est d'astreinte un jour on est d'astreinte tout le weekend
        # prend en compte les weekend prolonges
        if self.getCondition('cond7'):
            # weekend
            if slot.name == 'AT':
                if day.name == 'Samedi':
                    for i in [-1, 1, 2]:
                        self.force(getBlocslots(i, 'AT'))
                if day.name == 'Dimanche':
                    for i in [-2, -1, 1]:
                        self.force(getBlocslots(i, 'AT'))
                # et jours feries
                if day.name == 'Vendredi':
                    for i in [1, 2, 3]:
                        self.force(getBlocslots(i, 'AT'))
                if day.name == 'Lundi':
                    for i in [-3, -2, -1]:
                        self.force(getBlocslots(i, 'AT'))

        # si on est de garde vendredi, on est de garde dimanche
        if self.getCondition('cond5'):
            if day.name == "Vendredi" and slot.name == "G":
                self.force(getBlocslots(2, 'G'))
            elif day.name == "Dimanche" and slot.name == "G":
                self.force(getBlocslots(-2, 'G'))
