"""5 règles qualité distinctes appliquées à un enregistrement bronze avant passage en silver.

Chaque règle retourne (ok: bool, detail: str). L'appelant est responsable
de logguer chaque résultat dans log_qualite (une ligne par règle).
"""
from datetime import date, datetime

DEVISES_ATTENDUES = {"USD", "GBP", "CHF"}
SEUIL_FRAICHEUR_JOURS = 4  # au-delà, on considère la donnée périmée (au-delà d'un long week-end)


def check_completude(record: dict, devise_attendue: str) -> tuple[bool, str]:
    """Les champs indispensables sont-ils présents ?"""
    rates = record.get("rates", {})
    if "date" not in record or devise_attendue not in rates:
        return False, f"champ manquant (date ou taux pour {devise_attendue})"
    return True, "champs requis présents"


def check_exactitude(record: dict, devise_attendue: str) -> tuple[bool, str]:
    """Le taux est-il un nombre valide, positif et dans une plage plausible ?"""
    rates = record.get("rates", {})
    valeur = rates.get(devise_attendue)
    if valeur is None:
        return False, "taux absent"
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return False, f"taux non numérique : {valeur!r}"
    if not (0 < valeur < 1000):
        return False, f"taux hors plage plausible : {valeur}"
    return True, f"taux={valeur} valide"


def check_coherence(record: dict, devise_attendue: str) -> tuple[bool, str]:
    """La devise renvoyée correspond-elle à la devise demandée, et la base est-elle bien EUR ?"""
    if record.get("base") != "EUR":
        return False, f"base inattendue : {record.get('base')}"
    if devise_attendue not in record.get("rates", {}):
        return False, f"devise {devise_attendue} absente de la réponse"
    return True, "devise et base cohérentes"


def check_fraicheur(record: dict, execution_date: str) -> tuple[bool, str]:
    """La date renvoyée par la source n'est-elle pas trop ancienne par rapport à la date d'exécution ?"""
    date_recue = record.get("date")
    if not date_recue:
        return False, "date absente"
    try:
        d_recue = datetime.strptime(date_recue, "%Y-%m-%d").date()
        d_exec = datetime.strptime(execution_date, "%Y-%m-%d").date()
    except ValueError:
        return False, f"format de date invalide : {date_recue}"
    ecart = (d_exec - d_recue).days
    if ecart > SEUIL_FRAICHEUR_JOURS:
        return False, f"donnée périmée : {ecart} jours d'écart (seuil {SEUIL_FRAICHEUR_JOURS})"
    return True, f"écart={ecart}j, dans le seuil"


def check_unicite(devise: str, execution_date: str, deja_vus: set) -> tuple[bool, str]:
    """Pas de doublon (devise, date) déjà chargé dans ce run."""
    cle = (devise, execution_date)
    if cle in deja_vus:
        return False, f"doublon détecté pour {devise} / {execution_date}"
    deja_vus.add(cle)
    return True, "aucun doublon"


def evaluate_all(record: dict, devise: str, execution_date: str, deja_vus: set) -> list[tuple[str, bool, str]]:
    """Applique les 5 règles et retourne la liste (nom_regle, ok, detail)."""
    return [
        ("completude", *check_completude(record, devise)),
        ("exactitude", *check_exactitude(record, devise)),
        ("coherence", *check_coherence(record, devise)),
        ("fraicheur", *check_fraicheur(record, execution_date)),
        ("unicite", *check_unicite(devise, execution_date, deja_vus)),
    ]