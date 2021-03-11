import datetime
from src import DAYS, MONTHS, CANDIDATES
import json
import random

def generateDays(ndays=30, start=0, save=None):
	days = {}
	date = datetime.datetime.now()
	for _ in range(start):
		date += datetime.timedelta(days=1)
	for i in range(ndays):
		d = date.timetuple()
		wday = DAYS[d.tm_wday]
		ymonth = MONTHS[d.tm_mon]
		if wday in ["Samedi", "Dimanche"]:
			isHoliday = "oui"
			slots = ["AT", "G"]
		else:
			isHoliday = "non"
			slots = ["DG", "G"]
		days["J"+str(i+1)] = {"name": "{0} {1} {2} {3}".format(wday , d.tm_mday, ymonth, d.tm_year),
							  "ferie": isHoliday, "creneaux": slots}
		date += datetime.timedelta(days=1)
	if save:
		with open(save, "w") as f:
			json.dump(days, f, indent=4)

	return days


def generateCandidates(days, save=None):
	daynames = list(days.keys())
	candidates = {}
	for i, candidate in enumerate(CANDIDATES):
		id = 'J'+str(i+1)
		prenom, nom, statut = candidate.split(' ')



		def getRandomMinMax(mini=0, maxi=10):
			nmax = random.randint(mini, maxi)
			nmin = random.randint(0, nmax)
			return {"min": nmin, "max": nmax}

		nombre = {"total": {"min": random.choice([0,0,0,0,1,2]), "max": random.randint(3, 10)},#getRandomMinMax(0, 10),
				  "AT": {"min": None, "max": None},#getRandomMinMax(0, 2),
				  "DG": {"min": None, "max": None},#getRandomMinMax(0, 2),
				  "G":  {"min": None, "max": None}}#getRandomMinMax(0, 2)}

		conditions = {"cond0": True,
					  "cond1": random.choice([True, False, False, False]),
					  "cond2": random.choice([True, False, False, False]),
					  "cond3": random.choice([True, False, False, False]),
					  "cond4": random.choice([True, False, False, False])}

		nresents = random.randint(0, 3)
		nwishes = random.randint(0, 4)


		if statut == "junior":
			blocs = ["G2", "G3"]
			select = [[i, "G"] for i in random.choices(daynames, k=nresents+nwishes)]
			priority = 1
		else:
			blocs = random.sample(["G1", "G2", "G3", "DG1", "DG2", "DG3", "AT1", "AT2"], k=random.randint(6, 8))
			select = [[i, random.choice(days[i]['creneaux'])] for i in random.sample(daynames, k=nresents+nwishes)]
			priority = 1

		wishes = select[:nwishes]
		resents = select[nwishes:]

		candidates[id] = {"prenom": prenom, "nom": nom, "statut": statut,
						  "priorite": priority, "blocs": blocs,
						  "desiderata": {"wishes": wishes, "resents": resents},
						  "nombre": nombre,
						  "conditions": conditions}

	if save:
		with open(save, "w") as f:
			json.dump(candidates, f, indent=4)

	return candidates
