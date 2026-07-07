-- Vérification de l'idempotence du chargement gold
-- À exécuter après avoir rejoué plusieurs fois le DAG sur la même execution_date

-- 1. Aucune ligne dupliquée : un seul enregistrement par (date, devise)
--    Si cette requête renvoie des lignes, l'idempotence est rompue.
SELECT id_date, id_devise, COUNT(*) AS nb_lignes
FROM fact_taux_change
GROUP BY id_date, id_devise
HAVING COUNT(*) > 1;
-- Résultat attendu : 0 ligne

-- 2. Le load_ts avance bien à chaque rejeu (preuve que l'UPDATE a eu lieu,
--    pas un simple skip), mais le nombre total de lignes reste stable.
SELECT id_date, id_devise, taux_valeur, load_ts
FROM fact_taux_change
ORDER BY id_date DESC, id_devise
LIMIT 20;

-- 3. Comptage total de lignes en gold pour une date donnée : doit rester
--    égal au nombre de devises validées (<=3), quel que soit le nombre de
--    rejeux du DAG pour cette date.
SELECT id_date, COUNT(*) AS nb_devises_chargees
FROM fact_taux_change
WHERE id_date = TO_CHAR(CURRENT_DATE, 'YYYYMMDD')::INT
GROUP BY id_date;
