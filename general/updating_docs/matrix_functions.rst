Matrix functions
================

.. _Matrix:

The group of matrix functions comprises functions for vector and matrix operations and also functions for sparse matrix handling. MATLAB has two storage modes, full and sparse. Only nonzero entries and their indices are stored for sparse matrices. Sparse matrices are not created automatically. But once initiated, sparsity propagates. Operations on sparse matrices produce sparse matrices and operations on a mixture of sparse and full matrices also normally produce sparse matrices.

The following functions are described in this chapter:

**Vector and matrix operations**

+----------------------+--------------------------------------------------+
| ``[ ] ( )`` =        | Special characters                               |
+----------------------+--------------------------------------------------+
| ``' . , ;``          | Special characters                               |
+----------------------+--------------------------------------------------+
| ``:``                | Create vectors and do matrix subscripting       |
+----------------------+--------------------------------------------------+
| ``+ - * /``          | Matrix arithmetic                                |
+----------------------+--------------------------------------------------+
| ``abs``              | Absolute value                                   |
+----------------------+--------------------------------------------------+
| ``det``              | Matrix determinant                               |
+----------------------+--------------------------------------------------+
| ``diag``             | Diagonal matrices and diagonals of a matrix     |
+----------------------+--------------------------------------------------+
| ``inv``              | Matrix inverse                                   |
+----------------------+--------------------------------------------------+
| ``length``           | Vector length                                    |
+----------------------+--------------------------------------------------+
| ``max``              | Maximum element(s) of a matrix                  |
+----------------------+--------------------------------------------------+
| ``min``              | Minimum element(s) of a matrix                  |
+----------------------+--------------------------------------------------+
| ``ones``             | Generate a matrix of all ones                    |
+----------------------+--------------------------------------------------+
| ``size``             | Matrix dimensions                                |
+----------------------+--------------------------------------------------+
| ``sqrt``             | Square root                                      |
+----------------------+--------------------------------------------------+
| ``sum``              | Sum of the elements of a matrix                  |
+----------------------+--------------------------------------------------+
| ``zeros``            | Generate a zero matrix                           |
+----------------------+--------------------------------------------------+

**Sparse matrix handling**

+----------------------+--------------------------------------------------+
| ``full``             | Convert sparse matrix to full matrix            |
+----------------------+--------------------------------------------------+
| ``sparse``           | Create sparse matrix                             |
+----------------------+--------------------------------------------------+
| ``spy``              | Visualize sparsity structure                     |
+----------------------+--------------------------------------------------+

Special characters [ ] ( ) = ' . , ;
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: [ ] ( ) = ' . , ;

:Purpose:

    Special characters.

:Syntax:

.. code-block:: matlab

    [ ] ( ) = ' . , ;

:Description:

    **[ ]** 
        Brackets are used to form vectors and matrices.
    
    **( )** 
        Parentheses are used to indicate precedence in arithmetic expressions and to specify an element of a matrix.
    
    **=** 
        Used in assignment statements.
    
    **'** 
        Matrix transpose. ``X'`` is the transpose of ``X``. If ``X`` is complex, the apostrophe sign performs complex conjugate as well. Do ``X.'`` if only the transpose of the complex matrix is desired.
    
    **.**
        Decimal point. 314/100, 3.14 and 0.314e1 are all the same.
    
    **,**
        Comma. Used to separate matrix subscripts and function arguments.
    
    **;**
        Semicolon. Used inside brackets to end rows. Used after an expression to suppress printing or to separate statements.

:Examples:

    By the statement:

    .. code-block:: matlab

        a = 2

    the scalar ``a`` is assigned a value of 2. An element in a matrix may be assigned a value according to:

    .. code-block:: matlab

        A(2,5) = 3

    The statement:

    .. code-block:: matlab

        D = [ 1  2 ; 3  4 ]

    results in matrix:

    .. math::

        \mathbf{D} = \begin{bmatrix}
        1 & 2 \\
        3 & 4
        \end{bmatrix}

    stored in the matrix bank. To copy the contents of the matrix ``D`` to a matrix ``E``, use:

    .. code-block:: matlab

        E = D

    The character ' is used in the following statement to store the transpose of the matrix ``A`` in a new matrix ``F``:

    .. code-block:: matlab

        F = A'

:Note:

    These are MATLAB built-in characters.
: (colon operator)
^^^^^^^^^^^^^^^^^^

.. index:: :

:Purpose:

    Create vectors and do matrix subscripting.

:Description:

    The colon operator uses the following rules to create regularly spaced vectors:

    **j : k** 
        is the same as [ ``j``, ``j + 1, ... , k`` ]
    
    **j : i : k** 
        is the same as [ ``j``, ``j + i, j + 2i, ... , k`` ]

    The colon notation may also be used to pick out selected rows, columns, and elements of vectors and matrices:

    **A( : , j )** 
        is the ``j`` :th column of ``A``
    
    **A( i , : )** 
        is the ``i`` :th row of ``A``

:Examples:

    The colon ':' used with integers:

    .. code-block:: matlab

        d = 1:4

    results in a row vector:

    .. math::

        \mathbf{d} = \begin{bmatrix} 1 & 2 & 3 & 4 \end{bmatrix}

    stored in the workspace.

    The colon notation may be used to display selected rows and columns of a matrix on the terminal. For example, if we have created a 3-times-4 matrix ``D`` by the statement:

    .. code-block:: matlab

        D = [ d ; 2*d ; 3*d ]

    resulting in:

    .. math::

        \mathbf{D} = \begin{bmatrix}
        1 & 2 & 3 & 4 \\
        2 & 4 & 6 & 8 \\
        3 & 6 & 9 & 12
        \end{bmatrix}

    columns three and four are displayed by entering:

    .. code-block:: matlab

        D( :, 3:4 )

    resulting in:

    .. math::

        \mathbf{D}( :, 3:4 ) = \begin{bmatrix}
        3 & 4 \\
        6 & 8 \\
        9 & 12
        \end{bmatrix}

    In order to copy parts of the ``D`` matrix into another matrix the colon notation is used as:

    .. code-block:: matlab

        E( 3:4, 2:3 ) = D( 1:2, 3:4 )

    Assuming the matrix ``E`` was a zero matrix before the statement is executed, the result will be:

    .. math::

        \mathbf{E} = \begin{bmatrix}
        0 & 0 & 0 & 0 \\
        0 & 0 & 0 & 0 \\
        0 & 3 & 4 & 0 \\
        0 & 6 & 8 & 0
        \end{bmatrix}

:Note:

    This is a MATLAB built-in character.
+ - * / (arithmetic operators)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: + - * /

:Purpose:

    Matrix arithmetic.

:Syntax:

.. code-block:: matlab

    A + B
    A - B
    A * B
    A/s

:Description:

    Matrix operations are defined by the rules of linear algebra.

:Examples:

    An example of a sequence of matrix-to-matrix operations is:

    .. code-block:: matlab

        D = A + B - C

    A matrix-to-vector multiplication followed by a vector-to-vector subtraction may be defined by the statement:

    .. code-block:: matlab

        b = c - A * x

    and finally, to scale a matrix by a scalar ``s`` we may use:

    .. code-block:: matlab

        B = A/s

:Note:

    These are MATLAB built-in operators.
abs
^^^

.. index:: abs

:Purpose:

    Absolute value.

:Syntax:

.. code-block:: matlab

    B = abs(A)

:Description:

    ``B = abs(A)`` computes the absolute values of the elements of matrix ``A`` and stores them in matrix ``B``.

:Examples:

    Assume the matrix:

    .. math::

        \mathbf{C} = \begin{bmatrix}
        -7 & 4 \\
        -3 & -8
        \end{bmatrix}

    The statement:

    .. code-block:: matlab

        D = abs(C)

    results in a matrix:

    .. math::

        \mathbf{D} = \begin{bmatrix}
        7 & 4 \\
        3 & 8
        \end{bmatrix}

    stored in the workspace.

:Note:

    This is a MATLAB built-in function. For more information about the ``abs`` function, type ``help abs``.
det
^^^

.. index:: det

:Purpose:

    Matrix determinant.

:Syntax:

.. code-block:: matlab

    a = det(A)

:Description:

    ``a = det(A)`` computes the determinant of the matrix ``A`` and stores it in the scalar ``a``.

:Note:

    This is a MATLAB built-in function. For more information about the ``det`` function, type ``help det``.
diag
^^^^

.. index:: diag

:Purpose:

    Diagonal matrices and diagonals of a matrix.

:Syntax:

.. code-block:: matlab

    M = diag(v)
    v = diag(M)

:Description:

    For a vector ``v`` with *n* components, the statement ``M = diag(v)`` results in an *n* × *n* matrix ``M`` with the elements of ``v`` as the main diagonal.

    For a *n* × *n* matrix ``M``, the statement ``v = diag(M)`` results in a column vector ``v`` with *n* components formed by the main diagonal in ``M``.

:Note:

    This is a MATLAB built-in function. For more information about the ``diag`` function, type ``help diag``.
full
^^^^

.. index:: full

:Purpose:

    Convert sparse matrices to full storage class.

:Syntax:

.. code-block:: matlab

    A = full(S)

:Description:

    ``A = full(S)`` converts the storage of a matrix from sparse to full. If ``A`` is already full, ``full(A)`` returns ``A``.

:Note:

    This is a MATLAB built-in function. For more information about the ``full`` function, type ``help full``.
inv
^^^

.. index:: inv

:Purpose:

    Matrix inverse.

:Syntax:

.. code-block:: matlab

    B = inv(A)

:Description:

    ``B = inv(A)`` computes the inverse of the square matrix ``A`` and stores the result in the matrix ``B``.

:Note:

    This is a MATLAB built-in function. For more information about the ``inv`` function, type ``help inv``.
length
^^^^^^

.. index:: length

:Purpose:

    Vector length.

:Syntax:

.. code-block:: matlab

    n = length(x)

:Description:

    ``n = length(x)`` returns the dimension of the vector ``x``.

:Note:

    This is a MATLAB built-in function. For more information about the ``length`` function, type ``help length``.
max
^^^

.. index:: max

:Purpose:

    Maximum element(s) of a matrix.

:Syntax:

.. code-block:: matlab

    b = max(A)

:Description:

    For a vector ``a``, the statement ``b = max(a)`` assigns the scalar ``b`` the maximum element of the vector ``a``.

    For a matrix ``A``, the statement ``b = max(A)`` returns a row vector ``b`` containing the maximum elements found in each column vector in ``A``.

    The maximum element found in a matrix may thus be determined by ``c = max(max(A))``.

:Examples:

    Assume the matrix ``B`` is defined as:

    .. math::

        \mathbf{B} = \begin{bmatrix}
        -7 & 4 \\
        -3 & -8
        \end{bmatrix}

    The statement:

    .. code-block:: matlab

        d = max(B)

    results in a row vector:

    .. math::

        \mathbf{d} = \begin{bmatrix} -3 & 4 \end{bmatrix}

    The maximum element in the matrix ``B`` may be found by ``e = max(d)`` which results in the scalar ``e = 4``.

:Note:

    This is a MATLAB built-in function. For more information about the ``max`` function, type ``help max``.
min
^^^

.. index:: min

:Purpose:

    Minimum element(s) of a matrix.

:Syntax:

.. code-block:: matlab

    b = min(A)

:Description:

    For a vector ``a``, the statement ``b = min(a)`` assigns the scalar ``b`` the minimum element of the vector ``a``.

    For a matrix ``A``, the statement ``b = min(A)`` returns a row vector ``b`` containing the minimum elements found in each column vector in ``A``.

    The minimum element found in a matrix may thus be determined by ``c = min(min(A))``.

:Examples:

    Assume the matrix ``B`` is defined as:

    .. math::

        \mathbf{B} = \begin{bmatrix}
        -7 & 4 \\
        -3 & -8
        \end{bmatrix}

    The statement:

    .. code-block:: matlab

        d = min(B)

    results in a row vector:

    .. math::

        \mathbf{d} = \begin{bmatrix} -7 & -8 \end{bmatrix}

    The minimum element in the matrix ``B`` is then found by ``e = min(d)``, which results in the scalar ``e = -8``.

:Note:

    This is a MATLAB built-in function. For more information about the ``min`` function, type ``help min``.
ones
^^^^

.. index:: ones

:Purpose:

    Generate a matrix of all ones.

:Syntax:

.. code-block:: matlab

    A = ones(m,n)

:Description:

    ``A = ones(m,n)`` results in an ``m``-times-``n`` matrix ``A`` with all ones.

:Note:

    This is a MATLAB built-in function. For more information about the ``ones`` function, type ``help ones``.
%*************************************************************************
%\newpage
%\lhead[\bf prod]{}
%\rhead[]{\bf prod}
%\begin{tagx}
%\tag{Purpose:}
%Product of the elements in a matrix.
%
%\tag{Syntax:}

%{\sf a=prod(A)}

%\tag{Description:}

%For vectors, {\sf a=prod(x)} results in scalar {\sf a}
%as the product of all elements of {\sf x}.  For matrices,
%{\sf a = prod(X)} returns a row vector {\sf a} containing the 
%products of the elements found in each column vector of {\sf X}.

%The product of all elements in a matrix is determined 
%by {\sf c = prod(prod(X))}.   

%\tag{Note:}
%This is a MATLAB built-in function. For more information about 
%the {\sf prod} function, type {\sf help prod}.


%\end{tagx}
%*************************************************************************

size
^^^^

.. index:: size

:Purpose:

    Matrix dimensions.

:Syntax:

.. code-block:: matlab

    d = size(A)
    [m,n] = size(A)

:Description:

    ``d = size(A)`` returns a vector with two integer components, ``d = [m,n]``, from the matrix ``A`` with dimensions ``m`` times ``n``.

    ``[m,n] = size(A)`` returns the dimensions ``m`` and ``n`` of the *m* × *n* matrix ``A``.

:Note:

    This is a MATLAB built-in function. For more information about the ``size`` function, type ``help size``.
sparse
^^^^^^

.. index:: sparse

:Purpose:

    Create sparse matrices.

:Syntax:

.. code-block:: matlab

    S = sparse(A)
    S = sparse(m,n)

:Description:

    ``S = sparse(A)`` converts a full matrix to sparse form by extracting all nonzero matrix elements. If ``S`` is already sparse, ``sparse(S)`` returns ``S``.

    ``S = sparse(m,n)`` generates an m-times-n sparse zero matrix.

:Note:

    This is a MATLAB built-in function. For more information about the ``sparse`` function, type ``help sparse``.
spy
^^^

.. index:: spy

:Purpose:

    Visualize matrix sparsity structure.

:Syntax:

.. code-block:: matlab

    spy(S)

:Description:

    ``spy(S)`` plots the sparsity structure of any matrix ``S``. ``S`` is usually a sparse matrix, but the function also accepts full matrices and the nonzero matrix elements are plotted.

:Note:

    This is a MATLAB built-in function. For more information about the ``spy`` function, type ``help spy``.
sqrt
^^^^

.. index:: sqrt

:Purpose:

    Square root.

:Syntax:

.. code-block:: matlab

    B = sqrt(A)

:Description:

    ``B = sqrt(A)`` computes the square root of the elements in matrix ``A`` and stores the result in matrix ``B``.

:Note:

    This is a MATLAB built-in function. For more information about the ``sqrt`` function, type ``help sqrt``.
sum
^^^

.. index:: sum

:Purpose:

    Sum of the elements of a matrix.

:Syntax:

.. code-block:: matlab

    b = sum(A)

:Description:

    For a vector ``a``, the statement ``b = sum(a)`` results in a scalar ``a`` containing the sum of all elements of ``a``.

    For a matrix ``A``, the statement ``b = sum(A)`` returns a row vector ``b`` containing the sum of the elements found in each column vector of ``A``.

    The sum of all elements of a matrix is determined by ``c = sum(sum(A))``.

:Note:

    This is a MATLAB built-in function. For more information about the ``sum`` function, type ``help sum``.

zeros
^^^^^

.. index:: zeros

:Purpose:

    Generate a zero matrix.

:Syntax:

.. code-block:: matlab

    A = zeros(m,n)

:Description:

    ``A = zeros(m,n)`` results in an ``m``-times-``n`` matrix ``A`` of zeros.

:Note:

    This is a MATLAB built-in function. For more information about the ``zeros`` function, type ``help zeros``.