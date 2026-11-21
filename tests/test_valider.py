"""Vérification des traductions (outils/valider.py)."""

import json

import valider

LARGEURS = {"largeurs": {ch: 6 for ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'.,!?é "},
            "limites": {"histoire": 100}}
DICO = [(["Shadow"], ["Ombre"])]


def _verifier(tmp_path, entrees, base=None, rel="histoire/e100/x.json"):
    trad = tmp_path / "trad"
    p = trad / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entrees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return valider.verifier_fichier(p, trad=trad, base=base, largeurs=LARGEURS, dico=DICO)


def _niveaux(remarques):
    return [(r.niveau, r.id) for r in remarques]


def _e(fr, en="Hello.{PAGE}Bye.", **autres):
    return {"id": "MSG_001", "en": en, "fr": fr, **autres}


def test_traduction_correcte(tmp_path):
    assert _verifier(tmp_path, [_e("Salut.{PAGE}Ciao.")]) == []


def test_entree_vide_ignoree(tmp_path):
    assert _verifier(tmp_path, [_e("")]) == []


def test_nombre_de_pages(tmp_path):
    r = _verifier(tmp_path, [_e("Salut. Ciao.")])
    assert _niveaux(r) == [("ERREUR", "MSG_001")] and "1 page" in r[0].texte


def test_caractere_absent(tmp_path):
    r = _verifier(tmp_path, [_e("Señor.{PAGE}Ciao.")])
    assert r[0].niveau == "ERREUR" and "ñ" in r[0].texte


def test_balise_de_code_manquante(tmp_path):
    r = _verifier(tmp_path, [_e("Bye.", en="{f 2 4 0} has appeared!")])
    assert r[0].niveau == "ERREUR" and "{f 2 4 0}" in r[0].texte


def test_page_vide(tmp_path):
    r = _verifier(tmp_path, [_e("Salut.{PAGE} ")])
    assert r[0].niveau == "ERREUR" and "vide" in r[0].texte


def test_champ_inconnu(tmp_path):
    r = _verifier(tmp_path, [_e("Salut.{PAGE}Ciao.", note="?")])
    assert r[0].niveau == "ERREUR" and "note" in r[0].texte


def test_identifiant_en_double(tmp_path):
    r = _verifier(tmp_path, [_e(""), _e("")])
    assert r[0].niveau == "ERREUR" and "deux fois" in r[0].texte


def test_ligne_trop_large(tmp_path):
    r = _verifier(tmp_path, [_e("Une ligne beaucoup trop longue.{PAGE}Ciao.")])
    assert _niveaux(r) == [("ATTENTION", "MSG_001")] and "px" in r[0].texte


def test_espace_avant_ponctuation(tmp_path):
    r = _verifier(tmp_path, [_e("Quoi?{PAGE}Ciao.")])
    assert _niveaux(r) == [("ATTENTION", "MSG_001")] and "?" in r[0].texte


def test_ponctuation_double_permise(tmp_path):
    assert _verifier(tmp_path, [_e("Quoi !?{PAGE}Hein ??")]) == []


def test_double_espace_seulement_si_absente_de_l_anglais(tmp_path):
    assert _verifier(tmp_path, [_e("A  b.{PAGE}C.", en="X  y.{PAGE}Z.")]) == []
    r = _verifier(tmp_path, [_e("A  b.{PAGE}C.")])
    assert [x.texte for x in r] == ["double espace"]


def test_dictionnaire(tmp_path):
    r = _verifier(tmp_path, [_e("Un monstre !", en="A Shadow!")])
    assert _niveaux(r) == [("ATTENTION", "MSG_001")] and "Ombre" in r[0].texte


def test_anglais_modifie(tmp_path):
    base = [_e("", en="Hello.{PAGE}Bye.")]
    r = _verifier(tmp_path, [_e("", en="Hi.{PAGE}Bye.")], base=base)
    assert r[0].niveau == "ERREUR" and "en" in r[0].texte


def test_traduction_effacee(tmp_path):
    base = [_e("Salut.{PAGE}Ciao.")]
    r = _verifier(tmp_path, [_e("")], base=base)
    assert r[0].niveau == "ERREUR" and "effac" in r[0].texte


def test_json_invalide(tmp_path):
    trad = tmp_path / "trad"
    p = trad / "histoire" / "x.json"
    p.parent.mkdir(parents=True)
    p.write_text('[\n  {"id": "a", "en": "x", "fr": "y",}\n]\n', encoding="utf-8")
    r = valider.verifier_fichier(p, trad=trad, largeurs=LARGEURS, dico=DICO)
    assert r[0].niveau == "ERREUR" and r[0].ligne == 2


def test_numero_de_ligne_et_annotation(tmp_path):
    r = _verifier(tmp_path, [_e(""), {"id": "MSG_002", "en": "Bye.", "fr": "Señor."}])
    assert r[0].ligne == 10                      # la ligne du champ "fr" de MSG_002
    assert valider.annotation(r[0]).startswith("::error file=trad/histoire/e100/x.json,line=10")


def test_lire_dictionnaire(tmp_path):
    md = tmp_path / "d.md"
    md.write_text("| Anglais | Français | Statut |\n|---|---|---|\n"
                  "| Shadow / Shadows | Ombre / Ombres | ✅ |\n"
                  "| Velvet Room | Chambre de Velours *(abrégé : Velours)* | ✅ |\n"
                  "| Navigator | Navigatrice | 💬 |\n", encoding="utf-8")
    assert valider.lire_dictionnaire(md) == [(["Shadow", "Shadows"], ["Ombre", "Ombres"]),
                                            (["Velvet Room"], ["Chambre de Velours"])]


def test_nom_trop_long_pour_sa_case(tmp_path):
    court = {"id": "Medicine", "en": "Medicine", "max": 21, "fr": "Médicament"}
    long_ = {**court, "fr": "Médicament très fort"}             # 20 lettres, 22 octets
    assert _verifier(tmp_path, [court], rel="noms/objets.json") == []
    remarques = _verifier(tmp_path, [long_], rel="noms/objets.json")
    assert _niveaux(remarques) == [("ERREUR", "Medicine")]
    assert "22 octets" in remarques[0].texte


def test_le_maximum_ne_se_modifie_pas(tmp_path):
    base = [{"id": "Medicine", "en": "Medicine", "max": 21, "fr": ""}]
    nouveau = [{"id": "Medicine", "en": "Medicine", "max": 40, "fr": "Remède"}]
    remarques = _verifier(tmp_path, nouveau, base=base, rel="noms/objets.json")
    assert ("ERREUR", "Medicine") in _niveaux(remarques)
