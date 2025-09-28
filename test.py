class Salle:
    def __init__(self, numero, tempsNettoyage):
        self.numero = numero
        self.tempsNettoyage = tempsNettoyage
class Personne:
    def __init__(self, numero, tempsNettoyage, salles=None):
        self.numero = numero
        self.tempsNettoyage = tempsNettoyage
        self.salles = []

salle1 = Salle(1,21)
salle2 = Salle(2,20)
salle3 = Salle(3,16)
salle4 = Salle(4,18)
salle5 = Salle(5,13)

personne1 = Personne(1,0)
personne2 = Personne(2,0)
personne3 = Personne(3,0)

salles = [salle1, salle2, salle3, salle4, salle5]
personnes = [personne1, personne2, personne3]

for salle in salles:
    personneMin = 0
    Min = personnes[0].tempsNettoyage
    for personne in personnes:
        if personne.tempsNettoyage < Min:
            Min = personne.tempsNettoyage
            personneMin = personne.numero
    personnes[personneMin-1].tempsNettoyage += salle.tempsNettoyage
    personnes[personneMin-1].salles.append(salle.numero)


print([personne.salles for personne in personnes])