

# Utilizando o SHEBANG como na linha abaixo o script usa as variáveis
# de ambiente conforme conforme a versão de variáveis ou do Python
# como determinado na criação do Script Python assim independe de onde
# o Script Python estiver rodando para verificar as variáveis de ambiente
# no Linux utilizar o comando env e o comando which python para saber
# o caminho da versão do python para usar no SHEBANG
# Colocando python3 no final ao rodar o Script será verificado devido
# SHEBANG com o env em qual versão o Script deve rodar no caso então
# o Python3
# Devido eu já informar no SHEBANG que o Script vai rodar em Python ou
# Python 2 ou 3 mesmo que o Script seja renomeado de hello.py para hello
# ele funciona da mesma forma mesmo sem a extensão .py

#!/nix/store/sj74dzrygwdxpb54fv7zc6ry75ay4f3n-python-wrapped-0.1.0/bin/env python3


# #!/nix/store/sj74dzrygwdxpb54fv7zc6ry75ay4f3n-python-wrapped-0.1.0/bin/python
# SHEBANG - Comentário especial mensagem especial para o SO receber
# antes do código rodar no caso versão do python pelo comando which
# python 




# Este programa imprime Hello World

print("Hello World!")
print('marciano penaforte'.upper())
print(1 + 15)


input("Pressione Enter para fechar...")



