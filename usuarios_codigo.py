"""Usuários de DEMONSTRAÇÃO. Todos usam a mesma senha, que consta no README do Space."""

USUARIOS = {
    "paula.plan": {
        "nome": "Paula Planejamento Dias",
        "nivel": "planejamento",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$SKHJrRhxc7cApuyz5U10NA$DAT4oDRhcfV/HD4+D2HLuUfk3T2Aeu56I3XiZoNtul4",
    },
    "carlos.comite": {
        "nome": "Carlos Comitê Silva",
        "nivel": "comite",
        "unidade": "Gabinete da PGJ",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$FPYSTfHAlgn6yrivWH50VA$OEkrRkSWCYr80vqhPYKJUtiOYZxEkSCwN/ieQ0Ty1SQ",
    },
    "membro1": {
        "nome": "Membro 1",
        "nivel": "gestor_projeto",
        "unidade": "NUPA",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$TrfE6f8URIBjNa6hi7nZbg$GVG+xdl9CEiNXyhc3kOHHp7/SQRyzmEB4JzqI2B1D04",
    },
    "membro2": {
        "nome": "Membro 2",
        "nivel": "gestor_unidade",
        "unidade": "1ª PJ Parintins",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$QqLQDZN9FYle64cLa0gP7A$P7c9iv/6KQg+Hp7Mii9Lm0QP4H+g2XRQksdtghYqxjA",
    },
    "leitor.demo": {
        "nome": "Leitor de Demonstração",
        "nivel": "leitor",
        "unidade": "DPLAN",
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$TTL5ogjZKlzYcXPy1751Zw$YcWY4JpWU7YYKylcJfjlLhWRzNr0qGLyJY37LN8ry+Q",
    },
}
