"""Usuários de DEMONSTRAÇÃO. Todos usam a mesma senha, que consta no README do Space."""

USUARIOS = {
    "paula.plan": {
        "nome": "Paula Planejamento Dias",
        "nivel": "planejamento",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$NlCQ/+jSrOpT6BDhrmTHPw$ppvMo5H2ZSeR1rP9miYIdv4HgQxpP0OIwuEoYwPaePE",
    },
    "carlos.comite": {
        "nome": "Carlos Comitê Silva",
        "nivel": "comite",
        "unidade": "Gabinete da PGJ",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$o33OW+usSme2A21lSxo9Mw$zCs1Ria9S3rRr6ArMX5yCKYAUbycOD82SJYMvV8E6Kk",
    },
    "membro1": {
        "nome": "Membro 1",
        "nivel": "gestor_projeto",
        "unidade": "NUPA",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$uxK/lTig18NnEAvShiUDTA$dm9jjp5gJjrJ0FSPYUTbQxegzUS5/8TvRPAzckeQnmE",
    },
    "membro2": {
        "nome": "Membro 2",
        "nivel": "gestor_unidade",
        "unidade": "1ª PJ Parintins",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$3aAM9b+Bjn5LPtqF16xzAQ$LNrVsfyjaO49vmdImKJJ+Msq4OQIAIpIz/R00W6bP9U",
    },
    "leitor.demo": {
        "nome": "Leitor de Demonstração",
        "nivel": "leitor",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$HXtebLMMfL7kI0pbPlbcbQ$LjDBojEcp7HLdT82Kw56+JDrO7c+mUYQHBqX/BA1iCs",
    },
}
