"""Usuários de DEMONSTRAÇÃO. Todos usam a mesma senha, que consta no README do Space."""

USUARIOS = {
    "paula.plan": {
        "nome": "Paula Planejamento Dias",
        "nivel": "planejamento",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$TzKRgBm9MoFclmYqQcWQAA$jD1pbdxcTHEwXKbAi0cv3mfRmPYVbA7/6B4W6YTWjD0",
    },
    "carlos.comite": {
        "nome": "Carlos Comitê Silva",
        "nivel": "comite",
        "unidade": "Gabinete da PGJ",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$rMsqPCkUv2GxioQc1m+mgw$zt1J67lN53cEzlSuLHAolBNeom4wxEMS7TdoghaPzUM",
    },
    "membro1": {
        "nome": "Membro 1",
        "nivel": "gestor_projeto",
        "unidade": "NUPA",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$XwK2bEjRN+vJrgskCHtB2w$9zIHXllLQ3v7cakpN7wOGiYl/xPfc7Mw1mUtb5I5WUE",
    },
    "membro2": {
        "nome": "Membro 2",
        "nivel": "gestor_unidade",
        "unidade": "1ª PJ Parintins",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$XiAiOAjztCO2EOrl32rJYg$Fzbo9riGJJaUBv+m5bngKF9V4wlxpzSfD0dhh87nU5w",
    },
    "leitor.demo": {
        "nome": "Leitor de Demonstração",
        "nivel": "leitor",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$8oQh9QJciYOVGhUvUOm7rw$1SXLDX9s6dK74T/kMT7cc8tZPbt/0M0M7LXDCe3HSdw",
    },
}
