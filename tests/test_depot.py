"""Le garde-fou qui empêche un fichier du jeu d'entrer dans le dépôt."""

import subprocess

import sans_donnees_jeu


def _depot(tmp_path, fichiers):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for nom, contenu in fichiers.items():
        p = tmp_path / nom
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenu)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path


def test_sans_donnees_jeu_refuse_un_cpk(tmp_path, capsys):
    racine = _depot(tmp_path, {"romfs/data.cpk": b"CPK "})
    assert sans_donnees_jeu.verifier(racine) == 1
    assert "type de fichier interdit" in capsys.readouterr().out


def test_sans_donnees_jeu_refuse_un_nom_du_jeu(tmp_path, capsys):
    racine = _depot(tmp_path, {"notes/CTR-P-AQ2P.txt": b"x"})
    assert sans_donnees_jeu.verifier(racine) == 1
    assert "nom de fichier du jeu" in capsys.readouterr().out


def test_sans_donnees_jeu_refuse_un_gros_fichier(tmp_path, capsys):
    racine = _depot(tmp_path, {"assets/enorme.png": b"\0" * (2 * 1024 * 1024 + 1)})
    assert sans_donnees_jeu.verifier(racine) == 1
    assert "plus de 2 Mo" in capsys.readouterr().out


def test_sans_donnees_jeu_accepte_du_json(tmp_path):
    racine = _depot(tmp_path, {"trad/a.json": b"[]", "docs/00040000001D7600.md": b"# notes"})
    assert sans_donnees_jeu.verifier(racine) == 0
