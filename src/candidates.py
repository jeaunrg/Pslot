import random
import pdb
import copy
import numpy as np

class Candidate:
    def __init__(self, id, firstname, lastname, initiales, statut, priority=1):
        self.id = id
        self.firstname = firstname
        self.lastname = lastname
        self.initiales = initiales
        self.name = " ".join([firstname, lastname])
        self.statut = statut
        self.priority = priority
        self.schedule = None
        self.blocslots, self.final_blocslots = [], []
        self.wishes, self.resents = [], []
        self.penalities, self.scores  = {}, {}
        self.force_score = {}
        self.numbers = {'total': [0, 10000]}
        self.conditions = {}
        self.errors = {}

    def setConditions(self, conditions):
        self.conditions = conditions

    def addFinalBlocslot(self, blocslot):
        self.final_blocslots.append(blocslot)
        self.updateBlocslotPenalities(blocslot)

    def reset(self):
        self.final_blocslots = []
        self.scores = {}
        self.force_score = {}
        self.penalities = {k: 1 for k in self.penalities.keys()}
        self.updatePenalities()

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

    def force(self, blocslots, n=1):
        if not isinstance(blocslots, list):
            blocslots = [blocslots]
        for blocslot in blocslots:
            self.force_score[blocslot] = n

    def enable(self, blocslots, n=1):
        if not isinstance(blocslots, list):
            blocslots = [blocslots]
        for blocslot in blocslots:
            self.penalities[blocslot] = n

    def disable(self, blocslots, n=1):

        if not isinstance(blocslots, list):
            blocslots = [blocslots]
        for blocslot in blocslots:
            self.penalities[blocslot] = -n

    def isDisabled(self, blocslot):
        return self.penalities[blocslot] == -1

    def giveAccessToBlocs(self, bloc_names):
        for bloc_name in bloc_names:
            bloc = self.schedule.blocs[bloc_name]
            for blocslot in bloc.blocslots:
                if blocslot not in self.blocslots:
                    self.blocslots.append(blocslot)
                    self.enable(blocslot)
                blocslot.addCandidate(self)


    def getScore(self, blocslot, randomize=False):
        """
        score = [force, penality, wish_score, priority, random_score]
        force_score:      entier a 0 pour tous sauf en cas de force majeure
        penality:         entier qui permet de pénaliser (0) un candidat ou de le bloquer completement (-1)
        wish_score:     décrit si le slot est dans les 'rejets' (-1), les souhaits (1) ou autre (0)
        priority:         entier positif qui permet de priorisé un candidat sur un autre
        random_score:     flottant entre 0 et 1, permet de randomiser l'output
                        lorsque 2 candidats ont les mêmes scores pour un bloc-slot donné.
        """
        if blocslot in self.force_score.keys():
            score = [self.force_score[blocslot], self.penalities[blocslot]]
        else:
            score = [0, self.penalities[blocslot]]
        if blocslot.dayslot in self.wishes:
            score.append(1)
        elif blocslot.dayslot in self.resents:
            score.append(-1)
            score[0] = -1
        else:
            score.append(0)
        score.append(self.priority)
        if randomize:
            score.append(random.random())
        self.scores[blocslot] = score
        return score

    def freeze(self, slot_names=None):
        for blocslot in self.blocslots:
            if slot_names is None or blocslot.dayslot.slot.name in slot_names:
                if blocslot not in self.final_blocslots and not self.isDisabled(blocslot):
                    self.disable(blocslot)

    def penalize(self, slot_names=None):
        for blocslot in self.blocslots:
            if slot_names is None or blocslot.dayslot.slot.name in slot_names:
                if blocslot not in self.final_blocslots and not self.isDisabled(blocslot):
                    self.disable(blocslot, n=0)

    def updateCount(self):
        self.count = {k: 0 for k in self.numbers.keys()}
        self.count['total'] = len(self.final_blocslots)
        for blocslot in self.final_blocslots:
            if blocslot.dayslot.slot.name not in self.count.keys():
                self.count[blocslot.dayslot.slot.name] = 1
            else:
                self.count[blocslot.dayslot.slot.name] += 1

    def updatePenalities(self):
        self.updateCount()
        nmin, nmax = self.numbers['total']
        if self.count['total'] == nmax:
            self.freeze()
        else:
            if self.count['total'] == nmin:
                self.penalize()
            for slot_name, (nmin, nmax) in self.numbers.items():
                if self.count[slot_name] == nmax:
                    self.freeze(slot_name)
                elif self.count[slot_name] == nmin:
                    self.penalize(slot_name)

    def isObjectiveMet(self):
        for k, count in self.count.items():
            if count < self.numbers[k][0]:
                self.errors[k] = {'min. asked': self.numbers[k][0], 'given': count}
        return len(self.errors) == 0


    def getCondition(self, name):
        if name not in self.conditions.keys():
            self.conditions[name] = False
        return self.conditions[name]

    def getBlocslots(self, day, delta=0, slot=None):
        day = self.getDay(day, delta)
        if day is None:
            return None
        if slot is None:
            return day.blocslots
        else:
            return day.dayslots[slot].blocslots

    def getDay(self, day, delta=1):
        for _ in range(np.abs(delta)):
            if delta < 0:
                day = day.previous
            else:
                day = day.next
            if day is None:
                return
        return day

    def updateBlocslotPenalities(self, blocslot):
        self.updatePenalities()

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


        #----------------------- conditions obligatoires------------------------------#
        # si on fait une DG/AT/G un jour, on ne peut pas etre sur un autre creneau de DG/AT/G le meme jour
        if self.getCondition('cond0'):
            if slot.name == "DG":
                self.disable(getBlocslots(slotname="DG"))
                self.disable(getBlocslots(slotname="G"))
                self.disable(getBlocslots(-1, "G"))
            elif slot.name == "AT":
                self.disable(getBlocslots(slotname="AT"))
            elif slot.name == "G":
                self.disable(getBlocslots(slotname="G"))
                self.disable(getBlocslots(slotname="DG"))
                self.disable(getBlocslots(1, "DG"))

        #----------------------- conditions facultatives ------------------------------#
        # on ne peut pas enchainer 3 jours de gardes/demigardes/astreintes d'affile
        if self.getCondition('cond1'):
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

        # on ne peut pas faire 2 gardes/demigardes/astreintes le mm jour
        if self.getCondition('cond4'):
            self.disable(day.blocslots)

        # si on est de garde vendredi, on est de garde dimanche
        if self.getCondition('cond5'):
            if day.name == "Vendredi" and slot.name == "G":
                self.force(getBlocslots(2, 'G'))
            elif day.name == "Dimanche" and slot.name == "G":
                self.force(getBlocslots(-2, 'G'))

        # si on est d'astreinte un weekend on ne peut pas l'etre le weekend d'apres
        if self.getCondition('cond6'):
            if day.name == 'Samedi' and slot.name == 'AT':
                self.disable(getBlocslots(7, 'AT'))
                self.disable(getBlocslots(8, 'AT'))
                self.disable(getBlocslots(-6, 'AT'))
                self.disable(getBlocslots(-7, 'AT'))
            if day.name == 'Dimanche' and slot.name == 'AT':
                self.disable(getBlocslots(6, 'AT'))
                self.disable(getBlocslots(7, 'AT'))
                self.disable(getBlocslots(-7, 'AT'))
                self.disable(getBlocslots(-8, 'AT'))

        # si on est d'astreinte un jour on est d'astreinte tout le weekend
        if self.getCondition('cond7'):
            if day.name == 'Samedi' and slot.name == 'AT':
                self.force(getBlocslots(1, 'AT'))
            if day.name == 'Dimanche' and slot.name == 'AT':
                self.force(getBlocslots(-1, 'AT'))
