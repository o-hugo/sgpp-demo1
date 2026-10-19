"""Usuários de DEMONSTRAÇÃO. Todos usam a mesma senha, que consta no README do Space."""

USUARIOS = {
    "paula.plan": {
        "nome": "Paula Planejamento Dias",
        "nivel": "planejamento",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$TLMU9lYGkXsZRG+WGAvd/w$yAJrRoCyqbrpRD3FtYo8acygVEjDcrE13Q7Lm0hhWwU",
    },
    "carlos.comite": {
        "nome": "Carlos Comitê Silva",
        "nivel": "comite",
        "unidade": "Gabinete da PGJ",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$bSZtpkDUq5buCaam22zcBQ$XOhJdsvqg1Kg7agiuk+tGa/0VQpelYRun2kN1/mTQTA",
    },
    "membro1": {
        "nome": "Membro 1",
        "nivel": "gestor_projeto",
        "unidade": "NUPA",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$ksa3Q/LG+d4YT8ggB+BQ4w$VMmJl4GLjwg1czU9tZE5EEHBdwNaDyK1rk+LsWvVGqs",
    },
    "membro2": {
        "nome": "Membro 2",
        "nivel": "gestor_unidade",
        "unidade": "1ª PJ Parintins",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$tAv1+zElLiJ+SkC7SLoVvg$QdAlrCRmuguQvjF5oA4QS9bYqP4rI1KYf1LVD/2jNPI",
    },
    "leitor.demo": {
        "nome": "Leitor de Demonstração",
        "nivel": "leitor",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$3x77y1rxiI70A4LXnTc2Hw$dTRWP1HA9cez0F7XjtFGm1fwB4mZp+bnzMuA8McDcWE",
    },
}
