# Test automatique de la recherche dans les fiches.
# Lancer depuis le dossier du projet : python tests\test_recherche.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import app

# (question, début d'un passage qui doit apparaître parmi les résultats)
CAS = [
    ("Quand semer le riz en saison sèche dans le Delta ?", "Calendrier proposé"),
    ("Quand semer le riz en saison des pluies ?", "Calendrier proposé"),
    ("Faut-il repiquer ou semer directement ?", "Mode de semis"),
    ("Comment préparer ma parcelle avant le semis ?", "Préparation du terrain"),
    ("Quelles variétés sont adaptées à la vallée ?", "Variétés citées"),
    ("Quelles variétés supportent le sel ?", "Variétés tolérantes au sel"),
    ("Comment savoir si ma parcelle est salée ?", "Limite d'emploi"),
    ("La salinité fait-elle perdre beaucoup de rendement ?", "Le problème"),
    ("Quand faut-il récolter ?", "**Récolte**"),
    ("Quand récolter le riz ?", "**Récolte**"),
    ("Quand vider l'eau avant la récolte ?", "**Eau**"),
    ("Que se passe-t-il à Colonat ?", "Colonat"),
    ("Quels travaux sont prévus à Dagana ?", "Février et mars 2026"),
    ("Quelle est la différence entre les périmètres de Dagana et de Podor ?", "tableau A2.2.1"),
    ("Pourquoi les sols du Delta sont salés ?", "Pourquoi le Delta est salé"),
    ("Le riz augmente-t-il la salinité ?", "Idée clé"),
    ("Quel est le calendrier de culture du riz ?", "Calendrier proposé"),
]

# Questions qui ne doivent trouver aucun passage
SANS_REPONSE = [
    "Comment soigner les maladies du riz ?",
    "Quelle sera la météo demain à Ross-Béthio ?",
    "Quelle est la capitale de la France ?",
]

extraits = app.charger_extraits()
print(len(extraits), "passages chargés\n")

reussis = 0
for question, attendu in CAS:
    resultats = app.chercher(question, extraits)
    rang = None
    for i, e in enumerate(resultats):
        if attendu in e["texte"]:
            rang = i + 1
            break
    if rang:
        reussis += 1
        print("OK   (rang " + str(rang) + ")", question)
    else:
        print("RATE          ", question)

for question in SANS_REPONSE:
    resultats = app.chercher(question, extraits)
    if len(resultats) == 0:
        reussis += 1
        print("OK   (aucun passage)", question)
    else:
        print("RATE          ", question)

total = len(CAS) + len(SANS_REPONSE)
print("\nRésultat :", reussis, "sur", total)
