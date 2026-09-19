from __future__ import annotations
from collections.abc import Sequence
from Lexer import Token, TokenKind
from ast_nodes import (
    Block,
    Expr,
    FunctionDecl,
    Node,
    Parameter,
    PrintItem,
    Program,
    SourceSpan,
    Stmt,
    StringLiteral,
    TypeName,
    VarDecl,
    WhileStmt,
    BinaryExpr,
    BinaryOperator,
)


TYPE_START = {TokenKind.KW_INT, TokenKind.KW_BOOL, TokenKind.KW_VOID} #tipo do token
EXPRESSION_START = { #quais tokens pode iniciar uma expressao
    
    TokenKind.IDENTIFIER,
    TokenKind.INT_LITERAL,
    TokenKind.KW_FALSE,
    TokenKind.KW_TRUE,
    TokenKind.LEFT_PAREN,
    TokenKind.LOGICAL_NOT,
    TokenKind.MINUS,
}
STATEMENT_START = TYPE_START | { ###########
    TokenKind.IDENTIFIER,
    TokenKind.KW_IF,
    TokenKind.KW_WHILE,
    TokenKind.KW_RETURN,
    TokenKind.KW_PRINT,
    TokenKind.LEFT_BRACE,
}


TYPE_BY_TOKEN = {  #dicionario de conversao
    TokenKind.KW_INT: TypeName.INT,
    TokenKind.KW_BOOL: TypeName.BOOL,
    TokenKind.KW_VOID: TypeName.VOID,
}


class ParserError(Exception):  #erro
    def __init__(self, token: Token, expected: set[TokenKind]):
        self.token = token #token que causou o problema
        self.expected = frozenset(expected) #quais tokens seriam permititods inves do token que causou o prob
        super().__init__()

    @property
    def line(self) -> int:
        return self.token.line

    @property
    def column(self) -> int:
        return self.token.column

    def __str__(self) -> str: #erro em mensagem
        names = ", ".join(kind.name for kind in sorted(
            self.expected,
            key=lambda kind: kind.value,
        ))
        return (
            f"erro sintático em {self.line}:{self.column}: esperado {{{names}}}, "
            f"encontrado {self.token.kind.name} ({self.token.lexeme!r})"
        )


class Parser:
    def __init__(self, tokens: Sequence[Token]):  #recebe os tokens produzidos pelo lexer
        self.tokens = list(tokens) #coloca em uma lista
        if not self.tokens:
            raise ValueError("a sequência de tokens deve terminar em EOF") #ve setem eOF, deve aparecer somnte 1 vez e no fim
        if self.tokens[-1].kind is not TokenKind.EOF:
            raise ValueError("o último token deve ser EOF")
        if any(token.kind is TokenKind.EOF for token in self.tokens[:-1]):
            raise ValueError("EOF deve aparecer uma única vez, no final")
        self.current = 0 #comeca em 0

    def peek(self, offset: int = 0) -> Token:  #vai olhar o token atual, sem consukmir ele
        #da pra olhar pra frente com essa funcao, tipo peek(1) (lookahead)
        index = min(self.current + offset, len(self.tokens) - 1)
        return self.tokens[index] #retornar token atual

    def check(self, kind: TokenKind) -> bool: #verifica o tipo do token
        return self.peek().kind is kind #retorna como kind o tipo do token

    def advance(self) -> Token: #pega o token atual(consome) e vai para o proximo  ////////////////////////////////
        token = self.peek() #coloca o token atual em token
        if self.current < len(self.tokens) - 1:
            self.current += 1 #avanca pro proxi
        return token 

    def match(self, *kinds: TokenKind) -> Token | None:  #se for umt token consuma, se n, tudo bem tbm
        if self.peek().kind in kinds:
            return self.advance() 
        return None

    def expect(self, kinds: TokenKind | set[TokenKind]) -> Token:  #espera que o token esteja no lugar certo, c n estiver retirna erro
        expected = kinds if isinstance(kinds, set) else {kinds}
        token = self.peek()  #/////////////////////////
        if token.kind not in expected:
            raise ParserError(token, set(expected))
        return self.advance()

    @staticmethod
    def _token_span(token: Token) -> SourceSpan: #cria um sourcespan pra cada token
        return SourceSpan(
            token.line,
            token.column,
            token.line,
            token.column + len(token.lexeme),
        )

    @staticmethod
    def _start(value: Token | Node) -> tuple[int, int]: #pega posicao incial
        if isinstance(value, Node):
            return value.span.start_line, value.span.start_column
        return value.line, value.column

    @staticmethod
    def _end(value: Token | Node) -> tuple[int, int]: #pega a posicao final 
        if isinstance(value, Node):
            return value.span.end_line, value.span.end_column
        return value.line, value.column + len(value.lexeme)

    @classmethod
    def _span(cls, first: Token | Node, last: Token | Node) -> SourceSpan:
        start_line, start_column = cls._start(first)
        end_line, end_column = cls._end(last)
        return SourceSpan(start_line, start_column, end_line, end_column)

    def parse(self) -> Program: #comela com o simbolo inicial da gramatica
        return self.parse_program()

    # program ::= function* EOF  #*zero ou mais
    def parse_program(self) -> Program:
        start = self.peek()
        functions: list[FunctionDecl] = []
        while self.peek().kind in TYPE_START: #enquanto tiver vai chamando
            functions.append(self.parse_function())
        eof = self.expect(TokenKind.EOF) #espera um EOF no fim
        return Program(functions, span=self._span(start, eof))

    # function ::= type IDENTIFIER ... block
    def parse_function(self) -> FunctionDecl: #reconhece a funcao
        start = self.peek() #guarda token inicial para o span
        return_type = self.parse_type() #consome
        name = self.expect(TokenKind.IDENTIFIER)
        self.expect(TokenKind.LEFT_PAREN)
        parameters = (
            self.parse_parameter_list()
            if self.peek().kind in TYPE_START
            else []
        )
        self.expect(TokenKind.RIGHT_PAREN)
        body = self.parse_block()
        return FunctionDecl(
            return_type,
            name.lexeme,
            parameters,
            body,
            span=self._span(start, body),
        )

    # type ::= KW_INT | KW_BOOL | KW_VOID
    def parse_type(self) -> TypeName: #precisa bater com algm desses 3
        token = self.expect(TYPE_START)
        return TYPE_BY_TOKEN[token.kind] #converte

    def parse_parameter_list(self) -> list[Parameter]:
        #raise NotImplementedError("implemente parameter_list")

        parametros = [self.parse_parameter()] #pega o primeiro parametro
        while self.match(TokenKind.COMMA): # se tiver virgula, consome e vai no loop
            parametros.append(self.parse_parameter()) # pega o proximo parametro

        return parametros # devolve a lista de parametros

    def parse_parameter(self) -> Parameter: #cuida de um parametro
        #raise NotImplementedError("implemente parameter")

        inicio = self.peek() # guarda onde comecou
        tipo = self.parse_type() # reconhece o tipo
        nome = self.expect(TokenKind.IDENTIFIER) # exige o nome da variavel

        return Parameter(tipo, nome.lexeme, span=self._span(inicio, nome)) #retorna o parametro

    def parse_block(self) -> Block: # {}
        #raise NotImplementedError("implemente block")
        inicio = self.expect(TokenKind.LEFT_BRACE) # espera o {
        comandos = [] # lista de comandos
        while not self.check(TokenKind.RIGHT_BRACE): #enquanto n for }
            comandos.append(self.parse_statement()) #pega o comando
        fim = self.expect(TokenKind.RIGHT_BRACE) # espera o }
        return Block(comandos, span=self._span(inicio, fim))

    def parse_statement(self) -> Stmt: #controla, olha o token atual e decide oq fazer
        #raise NotImplementedError("implemente statement")
        tipo = self.peek().kind
        if tipo in TYPE_START:  # se comeca com int, bool ou void
            return self.parse_declaration()
        elif tipo == TokenKind.IDENTIFIER: # se comeca com nome(atribuicao ou chamada) 
            return self.parse_id_or_call_statement()  
        elif tipo == TokenKind.KW_IF: # se for if
            return self.parse_if_statement() 
        elif tipo == TokenKind.KW_WHILE: # se for while
            return self.parse_while_statement()
        elif tipo == TokenKind.KW_RETURN: # se for return
            return self.parse_return_statement()
        elif tipo == TokenKind.KW_PRINT: # se for print
            return self.parse_print_statement()
        elif tipo == TokenKind.LEFT_BRACE: # se for { bloco
            return self.parse_block()
        else: # se n for nenhum dos acima, da erro
            raise self.expect(STATEMENT_START) 

    def parse_id_or_call_statement(self) -> Stmt: #ve c é uma chamadna ou =
        raise NotImplementedError("implemente id_or_call_statement")

    def parse_declaration(self) -> Stmt: #
        #raise NotImplementedError("implemente declaration")
        inicio = self.peek() #guarda onde comecou
        tipo = self.parse_type() #pega o tipo(int, bool)
        nome = self.expect(TokenKind.IDENTIFIER) #pega o nome da variavel
        valor = None #comeca sem valor
        if self.match(TokenKind.ASSIGN): #se tiver um =, consome e pega a expressao
            valor = self.parse_expression()
        fim = self.expect(TokenKind.SEMICOLON) #espera o ; no final
        return VarDecl(tipo, nome.lexeme, valor, span=self._span(inicio, fim))

    def parse_if_statement(self) -> Stmt: 
        raise NotImplementedError("implemente if_statement")

    def parse_while_statement(self) -> Stmt:
        #raise NotImplementedError("implemente while_statement")
        inicio = self.expect(TokenKind.KW_WHILE) # espera e consome a palavra while
        self.expect(TokenKind.LEFT_PAREN) # espera o (
        condicao = self.parse_expression() #pega a expressao/condicao do while
        self.expect(TokenKind.RIGHT_PAREN) # espera o )
        corpo = self.parse_block() # le o bloco de codigo {...}
        return WhileStmt(condicao, corpo, span=self._span(inicio, corpo)) #retorna o while

    def parse_return_statement(self) -> Stmt:
        raise NotImplementedError("implemente return_statement")

    def parse_print_statement(self) -> Stmt:
        raise NotImplementedError("implemente print_statement")

    def parse_print_item(self) -> PrintItem:
        raise NotImplementedError("implemente print_item")

    def parse_string_literals(self) -> StringLiteral:
        raise NotImplementedError("implemente string_literals")

    def parse_expression(self) -> Expr:
        #raise NotImplementedError("implemente expression")
        return self.parse_logical_or() # expressao ::= logical_or

    def parse_logical_or(self) -> Expr:
        #raise NotImplementedError("implemente logical_or")
        expr = self.parse_logical_and() #le o lado esquerdo
        while self.match(TokenKind.LOGICAL_OR): #enquanto tiver ||
            direita = self.parse_logical_and() #le o lado direito
            expr = BinaryExpr(BinaryOperator.LOGICAL_OR, expr, direita, span=self._span(expr, direita)) # junta os dois lados
        return expr

    def parse_logical_and(self) -> Expr:
        #raise NotImplementedError("implemente logical_and")
        expr = self.parse_equality() #le o lado esquerdo
        while self.match(TokenKind.LOGICAL_AND): #enquanto tiver &&
            direita = self.parse_equality() #le o lado direito
            expr = BinaryExpr(BinaryOperator.LOGICAL_AND, expr, direita, span=self._span(expr, direita)) # junta os dois lados
        return expr

    def parse_equality(self) -> Expr:
        #raise NotImplementedError("implemente equality")
        expr = self.parse_relational() #le o lado esquerdo
        operadores = {TokenKind.EQUAL_EQUAL, TokenKind.NOT_EQUAL} #operadores de igualdade
        while self.peek().kind in operadores: #enquanto tiver == ou !=
            token = self.advance() #consome o "==" ou "!="
            if token.kind == TokenKind.EQUAL_EQUAL: #se for ==
                operador = BinaryOperator.EQUAL
            elif token.kind == TokenKind.NOT_EQUAL: #se for !=
                operador = BinaryOperator.NOT_EQUAL
            direita = self.parse_relational() #le o lado direito
            expr = BinaryExpr(operador, expr, direita, span=self._span(expr, direita)) # junta os dois lados
        return expr

    def parse_relational(self) -> Expr:
        raise NotImplementedError("implemente relational")

    def parse_additive(self) -> Expr:
        raise NotImplementedError("implemente additive")

    def parse_multiplicative(self) -> Expr:
        raise NotImplementedError("implemente multiplicative")

    def parse_unary(self) -> Expr:
        raise NotImplementedError("implemente unary")

    def parse_primary(self) -> Expr:
        raise NotImplementedError("implemente primary")

    def parse_arguments(self) -> list[Expr]:
        raise NotImplementedError("implemente arguments")

