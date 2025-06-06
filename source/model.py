# -*- coding: utf-8 -*-

# model.py



from dataclasses import dataclass, field
from typing      import List
DEBUG = False
class Visitor(metaclass=type):  # Replace multimeta with type or define multimeta elsewhere
  pass

@dataclass
class Node:
    lineNo: int = 0
    def accept(self, visitor, env):
        if DEBUG: print(f"Visitando {self.__class__.__name__} ")
        return visitor.visit(self, env)

class Assignment(Node):
    def __init__(self, location, expression):
        self.definition = "Assignment"
        self.location = location
        self.expression = expression

    def __repr__(self):
        return f'Assignment({self.location}, {self.expression})'

#
# 1.2 Printing
#     print expression ;


class Print(Node):
    def __init__(self, expression):
        self.definition = "Print"
        self.expr = expression

    def __repr__(self):
        return f'Print({self.expr})'

# 1.3 Conditional
#     if test { consequence } else { alternative }
#
class If(Node):
    def __init__(self, condition, if_statements, else_statements):
        self.definition = "If"
        self.condition = condition
        self.if_statements = if_statements
        self.else_statements = else_statements

    def __repr__(self):
        return f'Conditional({self.condition}, {self.if_statements}, {self.else_statements})'

# 1.4 While Loop
#     while test { body }
#
class While(Node):
    def __init__(self, condition, statements):
        self.definition = "While"
        self.condition = condition
        self.statements = statements

    def __repr__(self):
        return f'whilestatement({self.condition}, {self.statements})'

# 1.5 Break y Continue
#     while test {
#         ...
#         break;   // continue
#     }
#
class Break(Node):
    def __init__(self):
        self.definition = "Break"
        pass

    def __repr__(self):
        return f'breakstatement()'
    
class Continue(Node):
    def __init__(self):
        self.definition = "Continue"
        pass
    def __repr__(self):
        return f'continuestatement()'

# 1.6 Return un valor
#     return expresion ;
class Return(Node):
    def __init__(self, expression):
        self.definition = "Return"
        self.expr = expression

    def __repr__(self):
        return f'returnstatement({self.expr})'

# ----------------------------------------------------------------------
# Parte 2. Definictions/Declarations
#
# goxlang requiere que todas las variables y funciones se declaren antes de
# ser utilizadas.  Todas las definiciones tienen un nombre que las identifica.
# Estos nombres se definen dentro de un entorno que forma lo que se denomina
# un "ámbito".  Por ejemplo, ámbito global o ámbito local.

# 2.1 Variables.  Las Variables pueden ser declaradas de varias formas.
#
#     const name = value;
#     const name [type] = value;
#     var name type [= value];
#     var name [type] = value;+
#
# Las Constantes son inmutable. Si un valor está presente, el tipo puede ser
# omitido e inferir desde el tipo del valor.
#
class Variable(Node):
    def __init__(self, var_name, var_type = None, initial_value = None, is_const = False):
        self.definition = "Variable"
        self.is_const = is_const
        self.name = var_name
        self.type = var_type
        self.value = initial_value

    def __repr__(self):
        return f'Variable({self.name}, {self.type}, {self.value} , {self.is_const})'

# 2.2 Function definitions.
#
#     func name(parameters) return_type { statements }
#
# Una función externa puede ser importada usando una sentencia especial:
#
#     import func name(parameters) return_type;
#
#
class Function(Node):
    def __init__(self, imported, name, params, func_type, statements):
        self.definition = "Function"
        self.imported = imported
        self.name = name
        self.params = params
        self.func_type = func_type
        self.statements = statements

    def __repr__(self):
        return f'Function({self.imported}, {self.name}, {self.params}, {self.func_type}, {self.statements})'

# 2.3 Function Parameters
#
#     func square(x int) int { return x*x; }
#
# Un parametro de función (p.ej., "x int") es una clase de variable especial.
# Tiene un nombre y un tipo como una variable, pero es declarada como parte
# de la definición de una función, no como una declaración "var" separada.
#
class Parameter(Node):
    def __init__(self, param_name, param_type):
        self.definition = "Parameter"
        self.name = param_name
        self.type = param_type

    def __repr__(self):
        return f'Parameter({self.name}, {self.type})'

# ----------------------------------------------------------------------
# Parte 3. Expressions
#
# Las expresiones representan elementos que se evalúan y producen un valor concreto.
#
# goxlang define las siguientes expressiones y operadores
#
# 3.1 Literals
#     23           (Entero)
#     4.5          (Flotante)
#     true,false   (Booleanos)
#     'c'          (Carácter)
#
class Literal(Node):
    def __init__(self, value):
        self.definition = "Literal"
        self.value = value

    def __repr__(self):
        return f'Literal({self.value})'
    
class Integer(Node):
    def __init__(self, value):
        self.definition = "Integer"
        self.value = value

    def __repr__(self):
        return f'Integer({self.value})'

class Float(Node):
    def __init__(self, value):
        self.definition = "Float"
        self.value = value

    def __repr__(self):
        return f'Float({self.value})'

class Bool(Node):
    def __init__(self, value):
        self.definition = "Bool"
        self.value = value

    def __repr__(self):
        return f'Bool({self.value})'

class Char(Node):
    def __init__(self, value):
        self.definition = "Char"
        self.value = value

    def __repr__(self):
        return f'Char({self.value})'

# 3.2 Binary Operators
#     left + right   (Suma)
#     left - right   (Resta)
#     left * right   (Multiplicación)
#     left / right   (División)
#     left < right   (Menor que)
#     left <= right  (Menor o igual que)
#     left > right   (Mayor que)
#     left >= right  (Mayor o igual que)
#     left == right  (Igual a)
#     left != right  (Diferente de)
#     left && right  (Y lógico)
#     left || right  (O lógico)
#
class BinOp(Node):
    def __init__(self, operator,left, right):
        self.definition = "BinOp"
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self):
        return f'BinOp({self.operator}, {self.left}, {self.right})'

# 3.3 Unary Operators
#     +operand  (Positivo)
#     -operand  (Negación)
#     !operand  (Negación lógica)
#     ^operand  (Expandir memoria)
#
class UnaryOp(Node):
    def __init__(self, operator, operand):
        self.definition = "UnaryOp"
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return f'UnaryOp({self.operator}, {self.operand})'

# 3.4 Lectura de una ubicación (vea mas adelante)
#     location
#


# 3.5 Conversiones de tipo
#     int(expr)
#     float(expr)
#
class TypeCast(Node):
    def __init__(self, cast_type, expression):
        self.definition = "TypeCast"
        self.cast_type = cast_type
        self.expr = expression

    def __repr__(self):
        return f'Conversion({self.cast_type}, {self.expr})'

# 3.6 Llamadas a función
#     func(arg1, arg2, ..., argn)
#
class FunctionCall(Node):
    def __init__(self, name, arguments):
        self.definition = "FunctionCall"
        self.name = name
        self.args = arguments

    def __repr__(self):
        return f'FunctionCall({self.name}, {self.args})'

# ----------------------------------------------------------------------
# Parte 4: Locations
#
# Una ubicación representa un lugar donde se almacena un valor. Lo complicado
# de las ubicaciones es que se usan de dos maneras diferentes.
# Primero, una ubicación podría aparecer en el lado izquierdo de una asignación
# de esta manera:
#
#     location = expression;        // Almacena un valor dentro de location
#
# Sin embargo, una ubicación podria aparecer como parte de una expresión:
#
#     print location + 10;          // Lee un valor desde location
#
# Una ubicación no es necesariamente simple nombre de variable. Por ejemplo,
# considere el siguiente ejemplo en Python:
#
#     >>> a = [1,2,3,4]
#     >>> a[2] = 10                 // Almacena en ubicación "a[2]"
#     >>> print(a[2])               // Lee desde ubicación "a[2]"
#
# goxlang tiene dos tipos de locations (ubicaciones):
#
# 4.1 Ubicaciones primitivas
#
#     abc = 123;
#     print abc;
#
#     Cualquier nombre usado debe referirse a una definición de variable existente.
#     Por ejemplo, "abc" en este ejmeplo debe tener una declaración correspondiente
#     tal como
#
#     var abc int;

# 4.2 Direcciones de memoria. Un número entero precedido por una comilla invertida (``)
#
#     `address = 123;
#     print `address + 10;
#
# Nota: Históricamente, comprender la naturaleza de las ubicaciones ha sido
# una de las partes pas dificiles del proyecto del compilador.  Se espera
# mucho mas debate sobre este tema. Sugiero enfáticamente posponer el trabajo de las
# direcciones hasta mucho mas adelantes del proyecto.
class NamedLocation(Node):
    def __init__(self, expr):
        self.definition = "NamedLocation"
        if isinstance(expr, str):
            self.name = expr
        else:
            raise ValueError("Invalid NamedLocation expression")

    def __repr__(self):
        return f'NamedLocation({self.name})'

class MemoryLocation(Node):
    def __init__(self, expr, _type='int'):
        self.definition = "Memory"
        self.expr = expr
        self.type = _type

    def __repr__(self):
        return f'Memory({self.expr})'

# programs.py
#
# En las entrañas de su compilador, debe representar programas
# como estructuras de datos. En este archivo, codificará manualmente
# algunos programas goxlang simples usando el modelo de datos que
# se ha desarrollado en el archivo goxlang/model.py
#
# El propósito de este ejercicio es doble:
#
# 1. Asegúrese de comprender el modelo de datos de su compilador.
# 2. Tenga algunas estructuras de programas que pueda usar para pruebas
# y experimentación posteriores.
#
# Este archivo está dividido en secciones. Siga las instrucciones para
# cada parte. Es posible que se haga referencia a partes de este archivo
# en partes posteriores del proyecto. Planifique tener muchos debates.
#
#from model import *

# ---------------------------------------------------------------------
# Expression Simple
#
# Esto se le da a usted como un ejemplo

expr_source = "2 + 3 * 4"

expr_model = BinOp('+', Integer(2),
                        BinOp('*', Integer(3),
                        Integer(4)))

@dataclass
class Statement(Node):
  pass

@dataclass
class Program(Node):
    def __init__(self, stmts):
        self.stmts = stmts

    def __repr__(self):
        return f"Program({self.stmts})"