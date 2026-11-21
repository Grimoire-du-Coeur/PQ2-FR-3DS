"""Tables de noms du combat (battle/table/*.tbl)."""

import pytest

import tables
from fabrique import fabriquer_table_noms as fabriquer


@pytest.mark.parametrize("debuts", [True, False])
def test_relire_et_reecrire(debuts):
    brut = fabriquer(["Blank", "Agi", "Brand☆New☆Bam", "Agi"], debuts)
    t = tables.lire_table(brut)
    assert t.debuts is debuts and t.noms == ["Blank", "Agi", "Brand☆New☆Bam", "Agi"]
    assert tables.ecrire_table(t) == brut


def test_noms_a_traduire():
    brut = fabriquer(["BLANK", "Blank", "blank", "RESERVE SKILL", "", "Agi", "Rudra Ring", "Agi",
                      "総攻撃カメラ用", "Auto-Recover 25%"], True)
    assert tables.noms_a_traduire(brut) == ["Agi", "Rudra Ring", "Auto-Recover 25%"]
    assert tables.noms_a_traduire(brut, exclus={"Rudra Ring"}) == ["Agi", "Auto-Recover 25%"]


@pytest.mark.parametrize("debuts", [True, False])
def test_traduire_allonge_les_noms(debuts):
    brut = fabriquer(["Blank", "Luck Knack", "Agi", "Luck Knack"], debuts)
    nouveau = tables.traduire(brut, {"Luck Knack": "Don de chance", "Bufu": "absent de la table"})
    t = tables.lire_table(nouveau)
    assert t.debuts is debuts
    assert t.noms == ["Blank", "Don de chance", "Agi", "Don de chance"]


def test_table_illisible():
    brut = fabriquer(["Agi", "Bufu"], True)
    with pytest.raises(tables.ErreurTable):
        tables.lire_table(brut[:-1])


def test_trop_de_texte():
    brut = fabriquer(["Agi", "Bufu"], True)
    with pytest.raises(tables.ErreurTable, match="65 535"):
        tables.traduire(brut, {"Agi": "a" * 70000})
