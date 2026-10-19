"""Usuários de DEMONSTRAÇÃO. Todos usam a mesma senha, que consta no README do Space."""

USUARIOS = {
    "paula.plan": {
        "nome": "Paula Planejamento Dias",
        "nivel": "planejamento",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$4ajJZrZ1Ze7cNb4AaUzMtg$IVyS18/iTXbS2JFlwwoeEi/Bdg067V+I7BATxmCQQUo",
    },
    "carlos.comite": {
        "nome": "Carlos Comitê Silva",
        "nivel": "comite",
        "unidade": "Gabinete da PGJ",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$uIMwhnpa2oFnJbm1bTwaHw$odjzapbEXwOezbdAdixsuzvHtRUmun1H6CTOoLAjjos",
    },
    "membro1": {
        "nome": "Membro 1",
        "nivel": "gestor_projeto",
        "unidade": "NUPA",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$tAghS+Cc3R44JrxadeRoCA$ovV7CpM+UNyhJbC/PGSWLycjMyve8T+gdjguNXEYr70",
    },
    "membro2": {
        "nome": "Membro 2",
        "nivel": "gestor_unidade",
        "unidade": "1ª PJ Parintins",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$HfMva5kRBD9yLawTqh5P1g$mx+nTqr54q6fsrJq0hRDTuUfqa6ujzsan8uZINIlKLE",
    },
    "leitor.demo": {
        "nome": "Leitor de Demonstração",
        "nivel": "leitor",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$XrlcsFTbOsvA3aHqA8RM2A$1wgfp6s4y51XqrutpgEr7zVEeURz542MrRAt2jkEJ1s",
    },
}
