

# Nombre del Proyecto (Ej: SimpleCompiler)

Este proyecto es una implementación de un compilador/intérprete simple que procesa un lenguaje de programación personalizado. El proceso de compilación sigue un flujo de varias etapas, desde el análisis del código fuente hasta la ejecución en una máquina virtual de pila.

## 📜 Descripción del Flujo de Compilación

El proyecto está dividido en varios componentes modulares, donde la salida de una etapa es la entrada de la siguiente. La arquitectura sigue el siguiente orden:

`lexer` → `parser` → `model` → `checker` → `ircode` → `stack_machine`

---

## 🏗️ Estructura del Proyecto y Componentes

A continuación se detalla la responsabilidad de cada componente en el proceso:

### 1. `lexer` - Analizador Léxico
-   **Entrada**: Código fuente en un archivo de texto (`.gox`).
-   **Proceso**: Escanea el texto de entrada y lo descompone en una secuencia de **tokens**. Los tokens son las unidades mínimas del lenguaje, como palabras clave (`if`, `let`), identificadores (nombres de variables), operadores (`+`, `-`, `*`, `/`, `=`) y literales (números, cadenas). En esta fase se ignoran los espacios en blanco y los comentarios.
-   **Salida**: Una lista o flujo de tokens.

### 2. `parser` - Analizador Sintáctico
-   **Entrada**: La secuencia de tokens generada por el `lexer`.
-   **Proceso**: Verifica que la secuencia de tokens siga las reglas gramaticales del lenguaje. Construye un **Árbol de Sintaxis Abstracta (AST)**, que es una representación jerárquica de la estructura del código. Si la sintaxis es inválida, el parser reporta un error.
-   **Salida**: El AST que representa el programa.

### 3. `model` - Modelo Semántico
-   **Entrada**: El Árbol de Sintaxis Abstracta (AST).
-   **Proceso**: Recorre el AST para construir una estructura de datos que representa el "significado" del código. Esto generalmente incluye la creación de una **Tabla de Símbolos** para rastrear todas las variables, funciones y sus alcances (*scopes*).
-   **Salida**: Un modelo semántico enriquecido.

### 4. `checker` - Verificador de Tipos y Reglas
-   **Entrada**: El modelo semántico (AST anotado).
-   **Proceso**: Analiza el modelo para asegurar que se cumplan las reglas semánticas del lenguaje. Su tarea principal es la **verificación de tipos**, garantizando que las operaciones se realicen entre tipos de datos compatibles (ej: no permitir sumar un número y un texto).
-   **Salida**: Un modelo semántico verificado. Si hay errores, el proceso se detiene aquí.

### 5. `ircode` - Generador de Código Intermedio
-   **Entrada**: El modelo semántico verificado.
-   **Proceso**: Traduce la representación abstracta del código a un conjunto de instrucciones de bajo nivel, pero independiente de la arquitectura de la máquina. Este **Código Intermedio (IR)** es más fácil de optimizar y ejecutar que el AST.
-   **Salida**: Una secuencia de instrucciones de código intermedio.

### 6. `stack_machine` - Máquina de Pila
-   **Entrada**: El Código Intermedio (IR).
-   **Proceso**: Ejecuta las instrucciones del IR en una máquina virtual simple basada en una **pila**. Las operaciones (como suma, resta, asignación) manipulan valores empujándolos y sacándolos de la pila.
-   **Salida**: El resultado final de la ejecución del programa.

---



